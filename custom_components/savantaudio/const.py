DOMAIN = "savantaudio"
KNOWN_OUTPUTS = "known_outputs"
DEFAULT_PORT = 8085
DEFAULT_NAME = "SSA-3220"
DEFAULT_DEVICE = "SSA-3220"
SCAN_INTERVAL = timedelta(minutes=10)

DEFAULT_INPUTS = { f'Input{n}':f'Input {n}' for n in range(1,32) }
DEFAULT_OUTPUTS = { f'Output{n}':f'Output {n}' for n in range(1,20) }
