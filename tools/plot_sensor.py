#!/usr/bin/env python3
"""Record and plot the IR distance sensor readings from the sensor_test env.

Live:    python3 tools/plot_sensor.py [/dev/cu.usbmodem1101]
         Prints every line to the terminal while saving it to
         sensor_captures/<timestamp>.csv (one CSV per test); Ctrl+C stops the
         test and shows the plot. The port argument is optional.
Replay:  python3 tools/plot_sensor.py sensor_captures/<timestamp>.csv
         Only plots, writes nothing.
The plot shows the raw readings and, over them, a sliding-window mean of the
last AVG_WINDOW (3) readings, of the ADC value (the mV column is still saved in the CSV, just not plotted).

Serial lines look like "t:12345,raw:1234,avg:1230,mv:1010,min:80,max:3100"
(see src/test_sensor.cpp); the CSV columns are t_ms,raw,avg,mv.
Close the PlatformIO serial monitor first: the port takes one program at a time.
"""
import sys, os, datetime
import numpy as np
import matplotlib.pyplot as plt

DEFAULT_PORT = "/dev/cu.usbmodem1101"
COLUMNS = ("t", "raw", "avg", "mv")
AVG_WINDOW = 3   # sliding-window mean length drawn over the raw readings

def parse(line):
    """'t:1,raw:2,...' -> dict of ints, or None if it isn't a data line."""
    try:
        d = dict(kv.split(":") for kv in line.split(","))
        return {k: int(d[k]) for k in COLUMNS}
    except (ValueError, KeyError):
        return None

def record(port):
    import serial
    os.makedirs("sensor_captures", exist_ok=True)
    path = os.path.join("sensor_captures", datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv")
    rows = []
    # Open with DTR/RTS low: asserting them on open can reset the ESP32-S3 into
    # download mode (native USB), after which the firmware never runs.
    ser = serial.Serial()
    ser.port = port
    ser.baudrate = 115200
    ser.timeout = 1
    ser.dtr = False
    ser.rts = False
    ser.open()
    print(f"recording to {path} - Ctrl+C to stop and plot")
    with open(path, "w") as out:
        out.write("t_ms,raw,avg,mv\n")
        try:
            while True:
                line = ser.readline().decode(errors="ignore").strip()
                if not line:
                    continue
                print(line)
                r = parse(line)
                if r:
                    rows.append(r)
                    out.write(f"{r['t']},{r['raw']},{r['avg']},{r['mv']}\n")
                    out.flush()  # Ctrl+C loses nothing
        except KeyboardInterrupt:
            pass
    if rows:
        print(f"saved {len(rows)} readings in {path}")
    else:
        os.remove(path)
    return rows

def load(path):
    rows = []
    with open(path) as f:
        next(f)
        for l in f:
            t, raw, avg, mv = map(int, l.split(","))
            rows.append({"t": t, "raw": raw, "avg": avg, "mv": mv})
    return rows

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PORT
    rows = load(src) if src.endswith(".csv") else record(src)
    if not rows:
        sys.exit("no readings found")
    t0 = rows[0]["t"]
    t = np.array([(r["t"] - t0) / 1000 for r in rows])
    raw = np.array([r["raw"] for r in rows], dtype=float)

    def sliding_avg(x, n=AVG_WINDOW):
        """Mean of the last n readings (shorter window until n readings exist)."""
        c = np.cumsum(np.insert(x, 0, 0.0))
        idx = np.arange(1, len(x) + 1)
        lo = np.maximum(idx - n, 0)
        return (c[idx] - c[lo]) / (idx - lo)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(t, raw, color="tab:gray", lw=0.8, alpha=0.7, label="raw")
    ax.plot(t, sliding_avg(raw), color="tab:blue", lw=1.5, label=f"média móvel ({AVG_WINDOW} últimos)")
    ax.set_ylabel("ADC (0-4095)")
    ax.set_xlabel("seconds")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()

main()
