# import orangepi.pc
# from OPi import GPIO
from wiringpi import GPIO, HIGH, LOW
import wiringpi
from time import sleep, time
import logging
from threading import Timer
from os import getenv
import warnings

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG if getenv('DEBUG') == '1' else logging.INFO)


class Encoder:
    clk = None  # Board pin connected to the encoder CLK pin
    dt = None  # Same for the DT pin
    sw = None  # And for the switch pin
    polling_interval = None  # GPIO polling interval (in ms)
    sw_debounce_time = 250  # Debounce time (for switch only)

    # State
    clk_last_state = None
    sw_triggered = False  # Used to debounce a long switch click (prevent multiple callback calls)
    latest_switch_press = None

    step = 1  # Scale step from min to max
    # max_counter = 100  # Scale max
    # min_counter = 0  # Scale min
    counter = 0  # Initial scale position
    counter_loop = False  # If True, when at MAX, loop to MIN (-> 0, ..., MAX, MIN, ..., ->)

    inc_callback = None  # Clockwise rotation callback (increment)
    dec_callback = None  # Anti-clockwise rotation callback (decrement)
    chg_callback = None  # Rotation callback (either way)
    sw_callback = None  # Switch pressed callback

    def __init__(self, CLK=None, DT=None, SW=None, polling_interval=1, **params):

        if not CLK or not DT:
            raise BaseException("You must specify at least the CLK & DT pins")

        assert isinstance(CLK, int)
        assert isinstance(DT, int)
        self.clk = CLK
        self.dt = DT
        wiringpi.pinMode(self.clk, GPIO.INPUT)
        wiringpi.pinMode(self.dt, GPIO.INPUT)

        if SW is not None:
            assert isinstance(SW, int)
            self.sw = SW
            wiringpi.pinMode(self.sw, GPIO.INPUT)

        self.clk_last_state = wiringpi.digitalRead(self.clk)
        self.polling_interval = polling_interval

        self.setup(**params)

    def warnFloatDepreciation(self, i):
        if isinstance(i, float):
            warnings.warn(
                'Float numbers as `scale_min`, `scale_max`, `sw_debounce_time` or `step` will be deprecated in the '
                'next major release. Use integers instead.',
                DeprecationWarning)

    def setup(self, **params):

        # Note: boundaries are inclusive : [min_c, max_c]

        if 'loop' in params and params['loop'] is True:
            self.counter_loop = True
        else:
            self.counter_loop = False

        # if 'scale_min' in params:
        #     assert isinstance(params['scale_min'], int) or isinstance(params['scale_min'], float)
        #     self.min_counter = params['scale_min']
        #     self.counter = self.min_counter
        #     self.warnFloatDepreciation(params['scale_min'])
        # if 'scale_max' in params:
        #     assert isinstance(params['scale_max'], int) or isinstance(params['scale_max'], float)
        #     self.max_counter = params['scale_max']
        #     self.warnFloatDepreciation(params['scale_max'])
        if 'step' in params:
            assert isinstance(params['step'], int) or isinstance(params['step'], float)
            self.step = params['step']
            self.warnFloatDepreciation(params['step'])
        if 'inc_callback' in params:
            assert callable(params['inc_callback'])
            self.inc_callback = params['inc_callback']
        if 'dec_callback' in params:
            assert callable(params['dec_callback'])
            self.dec_callback = params['dec_callback']
        if 'chg_callback' in params:
            assert callable(params['chg_callback'])
            self.chg_callback = params['chg_callback']
        if 'sw_callback' in params:
            assert callable(params['sw_callback'])
            self.sw_callback = params['sw_callback']
        if 'sw_debounce_time' in params:
            assert isinstance(params['sw_debounce_time'], int) or isinstance(params['sw_debounce_time'], float)
            self.sw_debounce_time = params['sw_debounce_time']
            self.warnFloatDepreciation(params['sw_debounce_time'])

    def _switch_press(self):
        now = time() * 1000
        if not self.sw_triggered:
            if self.latest_switch_press is not None:
                # Only callback if not in the debounce delta
                if now - self.latest_switch_press > self.sw_debounce_time:
                    self.sw_callback()
            else:  # Or if first press since script started
                self.sw_callback()
        self.sw_triggered = True
        self.latest_switch_press = now

    def _switch_release(self):
        self.sw_triggered = False

    def _clockwise_tick(self):

        self.counter += self.step
        # if self.counter + self.step <= self.max_counter:
        #     self.counter += self.step
        # elif self.counter + self.step > self.max_counter:
        #     # If loop, go back to min once max is reached. Else, just set it to max.
        #     self.counter = self.min_counter if self.counter_loop is True else self.max_counter

        if self.inc_callback is not None:
            self.inc_callback(self.counter)
        if self.chg_callback is not None:
            self.chg_callback(self.counter)

    def _counterclockwise_tick(self):

        self.counter -= self.step
        # if self.counter - self.step >= self.min_counter:
        #     self.counter -= self.step
        # elif self.counter - self.step < self.min_counter:
        #     # If loop, go back to min once max is reached. Else, just set it to max.
        #     self.counter = self.max_counter if self.counter_loop is True else self.min_counter

        if self.inc_callback is not None:
            self.dec_callback(self.counter)
        if self.chg_callback is not None:
            self.chg_callback(self.counter)

    def watch(self):

        while True:
            try:
                # Switch part
                if self.sw_callback:
                    if wiringpi.digitalRead(self.sw) == LOW:
                        self._switch_press()
                    else:
                        self._switch_release()

                # Encoder part
                clkState = wiringpi.digitalRead(self.clk)
                dtState = wiringpi.digitalRead(self.dt)

                if clkState != self.clk_last_state:
                    if dtState != clkState:
                        self._clockwise_tick()
                    else:
                        self._counterclockwise_tick()

                self.clk_last_state = clkState
                sleep(self.polling_interval / 1000)

            except BaseException as e:
                logger.info("Exiting...")
                logger.info(e)
                break
        return
