#!/usr/bin/env python3
"""Plot piezo windows dumped by the firmware over Serial.

Live:     python3 tools/plot_piezo.py [/dev/cu.usbmodem1101]   (Ctrl+C to stop and plot;
          the port argument is optional, that one is the default)
Replay:   python3 tools/plot_piezo.py piezo_captures/<timestamp>.csv   (one saved test)
          python3 tools/plot_piezo.py capture.log                     (saved serial log; saves it as a new CSV)
          python3 tools/plot_piezo.py piezo_captures/<old folder>     (older per-hit CSV folders still open)

Serial lines look like "PZ,<piezo>,<hit>,<t_us>,<value>". One subplot per
piezo, each hit its own color. Each live/log run (one test) is saved as a
single CSV, piezo_captures/<timestamp>.csv, with columns piezo,hit,t_us,value;
replaying a CSV only plots, it writes nothing.
"""
import sys, os, re, collections, datetime
import matplotlib.pyplot as plt

DEFAULT_PORT = "/dev/cu.usbmodem1101"

def lines_from(src):
    if src.startswith("/dev/") or src.upper().startswith("COM"):
        import serial
        # Open with DTR/RTS low: asserting them on open can reset the ESP32-S3 into
        # download mode (native USB), after which the firmware never runs.
        ser = serial.Serial()
        ser.port = src
        ser.baudrate = 115200
        ser.timeout = 1
        ser.dtr = False
        ser.rts = False
        ser.open()
        try:
            while True:
                l = ser.readline().decode(errors="ignore").strip()
                if l:
                    print(l)
                    yield l
        except KeyboardInterrupt:
            return
    else:
        with open(src) as f:
            for l in f:
                yield l.strip()

def load_folder(path):
    """Folder of per-hit CSVs (piezo<P>_hit<NNN>.csv, columns t_us,value)."""
    data = {}
    for name in sorted(os.listdir(path)):
        m = re.fullmatch(r"piezo(\d+)_hit(\d+)\.csv", name)
        if not m:
            continue
        ts, vs = [], []
        with open(os.path.join(path, name)) as f:
            next(f)
            for l in f:
                t, v = l.split(",")
                ts.append(int(t)); vs.append(int(v))
        data[(int(m[1]), int(m[2]))] = (ts, vs)
    return data

def load_combined_csv(path):
    """Old single-file capture (columns piezo,hit,t_us,value)."""
    data = collections.defaultdict(lambda: ([], []))
    with open(path) as f:
        next(f)
        for l in f:
            p, h, t, v = l.split(",")
            data[(int(p), int(h))][0].append(int(t))
            data[(int(p), int(h))][1].append(int(v))
    return data

def capture(src):
    """Read PZ lines from a serial port or a saved log; save the whole run as ONE CSV."""
    data = collections.defaultdict(lambda: ([], []))  # (piezo, hit) -> (t_us, v)
    os.makedirs("piezo_captures", exist_ok=True)
    path = os.path.join("piezo_captures", datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv")
    with open(path, "w") as out:
        out.write("piezo,hit,t_us,value\n")
        for l in lines_from(src):
            if l.startswith("PZ,"):
                _, p, h, t, v = l.split(",")
                data[(int(p), int(h))][0].append(int(t))
                data[(int(p), int(h))][1].append(int(v))
            elif l.startswith("PZEND,"):  # window complete: append it now, so Ctrl+C loses nothing
                p, h = int(l.split(",")[1]), int(l.split(",")[2])
                ts, vs = data[(p, h)]
                out.writelines(f"{p},{h},{t},{v}\n" for t, v in zip(ts, vs))
                out.flush()
    if data:
        print(f"saved {len(data)} hits in {path}")
    else:
        os.remove(path)
    return data

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PORT
    if os.path.isdir(src):
        data = load_folder(src)
    elif src.endswith(".csv"):
        data = load_combined_csv(src)
    else:
        data = capture(src)
    if not data:
        sys.exit("no captures found")
    data = {k: ([t / 1000 for t in ts], vs) for k, (ts, vs) in data.items()}
    fig, axes = plt.subplots(3, 1, sharex=True, sharey=True, figsize=(9, 8))
    for p, ax in enumerate(axes, 1):
        hits = sorted(k for k in data if k[0] == p)
        # one distinct color per hit: tab10 for up to 10, else spread over turbo
        cmap = plt.cm.tab10 if len(hits) <= 10 else plt.cm.turbo
        for n, (_, h) in enumerate(hits):
            t, v = data[(p, h)]
            color = cmap(n % 10) if len(hits) <= 10 else cmap(n / max(len(hits) - 1, 1))
            ax.plot(t, v, ".-", ms=3, lw=0.9, color=color, alpha=0.8, label=f"hit {h}")
    for p, ax in enumerate(axes, 1):
        ax.set_ylabel(f"Piezo {p} (ADC)")
        ax.grid(alpha=0.3)
        if ax.get_legend_handles_labels()[0]:
            ax.legend(loc="upper right", fontsize=7, ncol=3)
    axes[-1].set_xlabel("ms since button press")
    plt.tight_layout()
    plt.show()

main()
