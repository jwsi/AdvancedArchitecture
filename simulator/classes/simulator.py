import pickle, curses, copy, time
from classes.instruction import Instruction
from classes.execution_unit import ExecutionUnit
from classes.register_file import RegisterFile
from classes.constants import debug, instruction_time
from classes.errors import Interrupt


class Simulator():
    """
    This is the class for the main processor simulator.
    """
    memory = None
    pc = None
    clock = 0
    register_file = RegisterFile().reg # Create the parent register file for the simulator
    strikes = 0
    instructions_executed = 0

    def __init__(self, input_file, stdscr):
        """
        Constructor for the Simulator class.
        :param input_file: input source machine code file.
        """
        f = open(input_file, "rb")
        self.memory = pickle.load(f)
        self.pc = pickle.load(f)
        f.close()
        self.register_file[29][1] = (max(self.memory) + 1) + (1000*4) # Initialise the stack pointer (1000 words).
        self.eu = ExecutionUnit(self.memory, self.register_file)
        self.stdscr = stdscr # Define the curses terminal
        if not debug:
            self.setup_screen(input_file) # Setup the initial curses layout


    def fetch(self):
        """
        This function fetches the appropriate instruction from memory.
        :return: raw binary instruction (string).
        """
        raw_instruction = ""
        try:
            for i in range(4):
                raw_instruction += self.memory[self.pc+i]
            self.pc += 4
            return {
                "pc" : self.pc - 4,
                "raw_instruction" : raw_instruction
            }
        except KeyError:
            return None


    def decode(self, fetch_object):
        """
        This function decodes the raw instruction into a Instruction object.
        :param raw_instruction: binary string of MIPS instruction.
        :return: Instruction object.
        """
        return Instruction(fetch_object["pc"], fetch_object["raw_instruction"])


    def execute(self, instruction):
        """
        This function executes the Instruction object.
        :param instruction: Instruction object to be executed.
        """
        pc, queue = self.eu.execute(instruction)
        return pc, queue


    def retire(self, queue):
        """
        This function writes back the pending results from the EUs to the register file.
        :param queue: queue of writebacks.
        """
        queue.commit(self.register_file, self.stdscr)


    def simulate(self):
        """
        The main simulate function controlling the:
        fetch, decode, execute and writeback.
        """
        stages = {
            "fetch" : None,
            "decode" : None,
            "execute" : None,
        }
        pipeline = [copy.copy(stages)]
        while True:
            self.clock += 1
            pipeline.append(copy.copy(stages))
            self.advance_pipeline(pipeline)
            if not debug:
                self.print_state(pipeline)


    def advance_pipeline(self, pipeline):
        """
        This function will advance the pipeline by one stage.
        :param pipeline: Pipeline to be advanced.
        """
        # Fetch Stage in Pipeline
        pipeline[self.clock]["fetch"] = self.fetch()
        # Decode Stage in Pipeline & Display All
        if pipeline[self.clock - 1]["fetch"] is not None:
            pipeline[self.clock]["decode"] = self.decode(pipeline[self.clock - 1]["fetch"])
        # Execute Stage in Pipeline
        if pipeline[self.clock - 1]["decode"] is not None:
            try:
                self.instructions_executed += 1
                pc, pipeline[self.clock]["execute"] = self.execute(pipeline[self.clock - 1]["decode"])
            except Interrupt:  # Catch Interrupts
                self.print_state(pipeline)
                raise Interrupt
            if pc != self.pc - 8:
                self.flush_pipeline(pipeline)
                self.pc = pc
        # Writeback stage in pipeline
        if pipeline[self.clock - 1]["execute"] is not None:
            self.retire(pipeline[self.clock - 1]["execute"])


    def flush_pipeline(self, pipeline):
        """
        This function flushes a particular pipeline.
        :param pipeline: Pipeline to be flushed.
        """
        pipeline[self.clock]["fetch"] = None
        pipeline[self.clock]["decode"] = None


    def print_state(self, pipeline):
        """
        This function prints the current state of the simulator to the terminal
        :param instruction: Instruction to be executed.
        """
        self.stdscr.addstr(3, 10, "Program Counter: " + str(self.pc), curses.color_pair(2))
        self.stdscr.addstr(4, 10, "Clock Cycles Taken: " + str(self.clock), curses.color_pair(3))
        self.stdscr.addstr(5, 10, "Instructions Executed: " + str(self.instructions_executed), curses.color_pair(5))
        for i in range(34):
            offset = 100
            if i > 20:
                offset += 20
            self.stdscr.addstr(i%20 + 2, offset, str(self.register_file[i][:2]).ljust(16))
        try:
            self.stdscr.addstr(9, 10, "Pipeline Fetch:     " + str(self.decode(pipeline[self.clock]["fetch"]).description(self.register_file).ljust(64)), curses.color_pair(4))
        except:
            self.stdscr.addstr(9, 10, "Pipeline Fetch:     Empty".ljust(72), curses.color_pair(4))
        try:
            self.stdscr.addstr(10, 10, "Pipeline Decode:    " + str(pipeline[self.clock]["decode"].description(self.register_file).ljust(64)), curses.color_pair(1))
        except:
            self.stdscr.addstr(10, 10, "Pipeline Decode:    Empty".ljust(72), curses.color_pair(1))
        try:
            self.stdscr.addstr(11, 10, "Pipeline Execute:   " + str(pipeline[self.clock-1]["decode"].description(self.register_file).ljust(64)), curses.color_pair(6))
        except:
            self.stdscr.addstr(11, 10, "Pipeline Execute:   Empty".ljust(72), curses.color_pair(6))
        try:
            self.stdscr.addstr(12, 10, "Pipeline Writeback: " + str(pipeline[self.clock-2]["decode"].description(self.register_file).ljust(64)), curses.color_pair(5))
        except:
            self.stdscr.addstr(12, 10, "Pipeline Writeback: Empty".ljust(72), curses.color_pair(5))
            time.sleep(instruction_time) # Need to account for no writeback pause.
        self.stdscr.refresh()


    def setup_screen(self, input_file):
        """
        Sets up the curses terminal with the appropriate colour scheme.
        """
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        self.stdscr.addstr(0, 100, "REGISTER FILE", curses.A_BOLD)
        self.stdscr.addstr(0, 10, "MACHINE INFORMATION", curses.A_BOLD)
        self.stdscr.addstr(2, 10, "Program: " + str(input_file), curses.color_pair(4))
        self.stdscr.addstr(4, 35, "Cycles per second: " + str(instruction_time), curses.color_pair(3))
        self.stdscr.addstr(7, 10, "PIPELINE INFORMATION", curses.A_BOLD)


    def shutdown(self):
        """
        Displays the final values of the return registers and does a memory dump.
        """
        self.stdscr.addstr(24,0, "Memory Dump:", curses.A_BOLD)
        self.stdscr.addstr(25,0, str(self.memory), curses.color_pair(3))
        self.stdscr.addstr(4, 100, str(self.register_file[2][:2]), curses.color_pair(3))
        self.stdscr.addstr(5, 100, str(self.register_file[3][:2]), curses.color_pair(3))
        self.stdscr.refresh()
        exit(0)