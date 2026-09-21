"""Edit pin numbers here before uploading to either glove."""

SAMPLE_RATE_HZ = 50
MAX_GESTURE_SECONDS = 3
MIN_TEMPLATE_SAMPLES = 3

# CD74HC4067: S0, S1, S2, S3 and common signal pin.
MUX_SELECT_PINS = (4, 5, 6, 7)
MUX_SIGNAL_PIN = 1
FLEX_CHANNELS = (0, 1, 2, 3, 4)

# GY-91 / MPU9250 I2C.
I2C_ID = 0
I2C_SDA_PIN = 8
I2C_SCL_PIN = 9
I2C_FREQUENCY = 400_000

# Right glove MAX98357A I2S.
I2S_ID = 0
I2S_BCLK_PIN = 16
I2S_LRC_PIN = 17
I2S_DIN_PIN = 18
I2S_RATE = 16_000
I2S_BUFFER_BYTES = 8_192

# Replace these after running tools/show_mac.py on both boards.
LEFT_HAND_MAC = None
RIGHT_HAND_MAC = None

# Motion segmentation. Values are learned from startup noise; these are ratios,
# not fixed sensor readings.
MOTION_START_SIGMA = 4.0
MOTION_STOP_SIGMA = 2.0
MOTION_QUIET_FRAMES = 15
MOTION_PRE_ROLL_FRAMES = 10

