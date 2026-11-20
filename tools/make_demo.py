"""Build the demo video from REAL runs of the game and its checks.

    .venv/bin/python tools/make_demo.py --out demo.mp4

Gameplay segments are recorded with the built-in bot (--autoplay) and are labelled
"BOT TỰ CHƠI" on screen. Terminal cards show the actual output of commands executed
while the video is being built. Needs: pip install imageio-ffmpeg (Pillow ships with Ursina).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H = 1280, 720
BG, GOLD, TXT, DANGER = (14, 20, 48), (242, 193, 78), (245, 241, 230), (255, 90, 95)


def font(size, mono=False):
    names = (["consola.ttf", "DejaVuSansMono.ttf", "Menlo.ttc"] if mono
             else ["arial.ttf", "DejaVuSans.ttf", "Arial.ttf"])
    dirs = ["C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu", "/System/Library/Fonts",
            "/Library/Fonts"]
    for d in dirs:
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def ff(*args):
    subprocess.run([FF, "-y", "-loglevel", "error", *args], check=True)


def card(path, title, lines, mono=False, note=None):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((60, 40), title, font=font(40), fill=GOLD)
    f = font(19 if mono else 26, mono)
    y = 110
    for ln in lines:
        col = DANGER if ("FAIL" in ln or "Error" in ln) else TXT
        d.text((60, y), ln, font=f, fill=col)
        y += 26 if mono else 38
    if note:
        d.text((60, H - 60), note, font=font(20), fill=(180, 190, 220))
    im.save(path)


def label(path, text):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font(24)
    w = d.textlength(text, font=f)
    d.rounded_rectangle((W - w - 40, H - 120, W - 16, H - 80), 8, fill=(0, 0, 0, 170))
    d.text((W - w - 28, H - 116), text, font=f, fill=GOLD)
    im.save(path)


def seg_still(img, secs, out, lab=None, tmp=None):
    if lab:
        lp = os.path.join(tmp, os.path.basename(out) + "_lab.png")
        label(lp, lab)
        ff("-loop", "1", "-t", str(secs), "-i", img, "-i", lp, "-filter_complex",
           "[0]scale=%d:%d,setsar=1[a];[a][1]overlay=0:0,format=yuv420p" % (W, H),
           "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", out)
    else:
        ff("-loop", "1", "-t", str(secs), "-i", img, "-vf", "scale=%d:%d,setsar=1,format=yuv420p" % (W, H),
           "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", out)


def seg_record(args, secs, out, lab, tmp):
    d = tempfile.mkdtemp(dir=tmp)
    prefix = os.path.join(d, "f")
    subprocess.run([PY, "-m", "lantern.app", *args, "--record", prefix, "--record-seconds", str(secs)],
                   cwd=ROOT, capture_output=True, timeout=600)
    lp = os.path.join(tmp, os.path.basename(out) + "_lab.png")
    label(lp, lab)
    ff("-framerate", "30", "-i", prefix + "_%04d.png", "-i", lp, "-filter_complex",
       "[0]scale=%d:%d,setsar=1[a];[a][1]overlay=0:0,format=yuv420p" % (W, H),
       "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", out)
    shutil.rmtree(d, ignore_errors=True)


def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=900)
    return (r.stdout + r.stderr).splitlines(), r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="demo.mp4")
    ap.add_argument("--live", help="optional mp4 of the author playing live, inserted after the intro")
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="ddl_demo_")
    segs = []

    def add(name):
        p = os.path.join(tmp, name)
        segs.append(p)
        return p

    img = lambda n: os.path.join(ROOT, "docs", "img", n)  # noqa: E731
    c = os.path.join(tmp, "intro.png")
    card(c, "Đảo Đèn Lồng – demo v1.0.0", [
        "Game 3D: Mây gom đom đóm, giữ các Đèn Lồng Lớn sáng tới bình minh.",
        "Python + Ursina/Panda3D · Test Contract v1.3 · 4 phase SDLC với AI.",
        "",
        "Nội dung: gameplay 3 Đêm · giao diện · test · scenario · benchmark · soak.",
        "",
    ] + (["Phần 1: tác giả CHƠI TRỰC TIẾP bằng bàn phím + chuột (nhãn \"NGƯỜI CHƠI THẬT\").",
           "Phần 2: BOT tự chơi (--autoplay) để giới thiệu Đêm 2, 3 (nhãn \"BOT TỰ CHƠI\")."]
          if a.live else
          ["LƯU Ý: các đoạn gameplay trong video này do BOT tự chơi (--autoplay),",
           "không phải người chơi. Nhãn \"BOT TỰ CHƠI\" hiện ở góc màn hình."]))
    seg_still(c, 7, add("00_intro.mp4"))
    if a.live:
        live = add("01_live.mp4")
        lp = os.path.join(tmp, "live_lab.png")
        label(lp, "NGƯỜI CHƠI THẬT (tác giả) · bàn phím + chuột")
        ff("-i", a.live, "-i", lp, "-filter_complex",
           "[0]scale=%d:%d,setsar=1[v];[v][1]overlay=0:0,format=yuv420p" % (W, H), "-r", "30", "-an",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", live)
    print("recording gameplay...", flush=True)
    seg_record(["--autoplay", "--night", "1"], 45, add("10_n1.mp4"), "BOT TỰ CHƠI · Đêm 1 – Đảo Bến", tmp)
    seg_record(["--autoplay", "--night", "2"], 20, add("11_n2.mp4"), "BOT TỰ CHƠI · Đêm 2 – Đảo Cau", tmp)
    seg_record(["--autoplay", "--night", "3"], 20, add("12_n3.mp4"), "BOT TỰ CHƠI · Đêm 3 – Đảo Chuông", tmp)
    seg_record(["--autoplay", "--night", "3", "--overview"], 6, add("13_n3o.mp4"),
               "Đảo Chuông nhìn từ trên: 3 tầng, dốc, tháp chuông", tmp)
    for i, (n, t) in enumerate([("ui_menu.png", "Menu chính"), ("ui_pause.png", "Tạm dừng"),
                                ("ui_settings.png", "Cài đặt (âm lượng, độ nhạy, mù màu, giảm chuyển động, chữ lớn)"),
                                ("ui_keys_conflict.png", "Đổi phím: phát hiện trùng phím"),
                                ("ui_leaderboard.png", "Bảng xếp hạng top 10 (lưu đĩa)")]):
        seg_still(img(n), 3.5, add("2%d_ui.mp4" % i), "Ảnh chụp từ game · " + t, tmp)

    print("running checks...", flush=True)
    out, rc = run([PY, "-m", "unittest", "discover", "-s", "tests", "-t", "."])
    c = os.path.join(tmp, "t1.png")
    card(c, "$ python -m unittest discover -s tests -t .", [l for l in out if l.strip()][-6:] +
         ["", "exit code: %d" % rc], mono=True, note="Output thật, chạy lúc dựng video")
    seg_still(c, 7, add("30_tests.mp4"))
    out, rc = run([PY, "tools/run_scenarios.py", "--phase", "demo"])
    shutil.rmtree(os.path.join(ROOT, "docs", "proof", "demo"), ignore_errors=True)
    c = os.path.join(tmp, "t2.png")
    rows = [l for l in out if l.strip()]
    n_pass = sum(" PASS" in l for l in rows)
    half = (len(rows) + 1) // 2
    two_col = ["%-36s %s" % (rows[i], rows[i + half] if i + half < len(rows) else "") for i in range(half)]
    card(c, "$ python tools/run_scenarios.py", ["(mỗi scenario chạy 2 lần, so output từng byte)", ""] +
         two_col + ["", "%d/%d PASS   exit code: %d" % (n_pass, len(rows), rc)], mono=True,
         note="Output thật, chạy lúc dựng video")
    seg_still(c, 8, add("31_scen.mp4"))
    bj = os.path.join(tmp, "bench.json")
    seg_record(["--bench", "--seed", "42", "--out", os.devnull], 10, add("32_bench.mp4"),
               "Cảnh benchmark: 200 Bóng Mực · 100 đom đóm · camera bay vòng", tmp)
    run([PY, "-m", "lantern.app", "--bench", "--seed", "42", "--duration", "10", "--out", bj])
    b = json.load(open(bj, encoding="utf-8"))
    c = os.path.join(tmp, "t3.png")
    card(c, "$ python -m lantern.app --bench --seed 42 --duration 10", [
        "avg_fps      %6.1f   (ngưỡng >= 60)" % b["avg_fps"],
        "p1_low_fps   %6.1f   (ngưỡng >= 30)" % b["p1_low_fps"],
        "frame_ms_p95 %6.2f" % b["frame_ms_p95"],
        "load_ms      %6d   (ngưỡng <= 10000)" % b["load_ms"],
        "peak_mem_mb  %6.1f" % b["peak_mem_mb"],
        "frames       %6d" % b["frames"], "", b["renderer"], b["os"]], mono=True,
        note="Output thật lúc dựng video (bản 10 s). bench.json chính thức (30 s): 104.7 / 35.4. "
             "p1_low trên GPU tích hợp này dao động quanh 30.")
    seg_still(c, 8, add("33_bench.mp4"))
    sj = os.path.join(tmp, "soak.json")
    run([PY, "-m", "lantern.soak", "--seed", "7", "--nights", "10", "--out", sj])
    s = json.load(open(sj, encoding="utf-8"))
    c = os.path.join(tmp, "t4.png")
    card(c, "$ python -m lantern.soak --seed 7 --nights 10", [
        "nights      %d" % s["nights"], "crashes     %d   (ngưỡng = 0)" % s["crashes"],
        "mem_start   %.1f MB" % s["mem_start_mb"],
        "mem_end     %.1f MB   (ngưỡng <= 1.2 x start)" % s["mem_end_mb"],
        "results     %s" % ", ".join(s["results"])], mono=True, note="Output thật, chạy lúc dựng video")
    seg_still(c, 6, add("34_soak.mp4"))
    log, _ = run(["git", "log", "--oneline", "-12"])
    tags, _ = run(["git", "tag", "--list"])
    c = os.path.join(tmp, "end.png")
    card(c, "Git, tag, harness AI", ["$ git tag --list", "  " + "  ".join(tags), "",
                                     "$ git log --oneline -12"] + ["  " + l[:95] for l in log] +
         ["", "Harness: AGENTS.md · Stop hook (chặn khi test đỏ) · skill verify-phase · CI Ubuntu+macOS"],
         mono=True)
    seg_still(c, 8, add("40_end.mp4"))

    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for p in segs:
            f.write("file '%s'\n" % p.replace("\\", "/"))
    silent = os.path.join(tmp, "silent.mp4")
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent)
    music = os.path.join(ROOT, "lantern", "assets", "sounds", "music.wav")
    ff("-i", silent, "-stream_loop", "-1", "-i", music, "-shortest", "-c:v", "copy", "-c:a", "aac",
       "-b:a", "96k", "-movflags", "+faststart", a.out)
    shutil.rmtree(tmp, ignore_errors=True)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
