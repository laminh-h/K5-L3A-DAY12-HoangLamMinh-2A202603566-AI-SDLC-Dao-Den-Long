# Đảo Đèn Lồng

> **Video demo:** *(sẽ thêm ở Phase 4)* · Đề bài lab: [docs/lab/](docs/lab/README.md)

Game 3D góc nhìn thứ ba. Bạn điều khiển Mây, gom đom đóm để thắp lại 5 Đèn Lồng Lớn của Đảo Bến trước bình minh, và né Bóng Mực trong sương đen.

## Cài đặt và chạy (macOS / Linux, Python ≥ 3.10)

```bash
git clone <repo> && cd K5-L3A-DAY12-HoangLamMinh-2A202603566-AI-SDLC-Dao-Den-Long
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt   # chỉ bản 3D cần (ursina)
.venv/bin/python -m lantern.app                                                 # chơi
```

Dùng venv để tránh lỗi PEP 668 "externally-managed-environment" trên Python của Homebrew và Debian/Ubuntu mới.

Chế độ headless **không cần cài gì** (chỉ dùng Python stdlib):

```bash
python3 -m lantern.headless --seed 1 --night 1 --ticks 600 --out out.jsonl \
    [--scenario s.json] [--inputs i.json] [--snapshot-every 10]
```

Theo Test Contract v1.0, xem [game.contract.json](game.contract.json). Mã thoát: 0 chạy xong, 2 khi file inputs/scenario/tham số sai, 1 cho lỗi khác.

## Điều khiển

| Phím | Hành động |
|---|---|
| W A S D | Di chuyển (theo hướng camera) |
| Chuột | Xoay camera |
| Space | Nhảy |
| E | Nạp ánh sáng vào đèn gần nhất |
| Q / chuột trái | Tỏa sáng: choáng và đẩy lùi Bóng Mực, tốn 1 đom đóm |
| R | Chơi lại sau khi thắng/thua |

## Luật và cách tính điểm

- Mang tối đa 10 đom đóm. Nạp đủ 10 vào một đèn thì đèn sáng.
- Bóng Mực không vào được vùng 5 m quanh đèn **đã thắp**.
- Bị chạm: mất 1 flame (có 3), rơi mất một nửa số đom đóm đang mang, bất tử 1.5 s.
- **Thắng:** thắp đủ 5 đèn. **Thua:** hết flame, hoặc hết 300 s (bình minh).
- **Không có rơi khỏi đảo** (`fall_enabled: false`): người chơi bị giữ trong bán kính đảo 40 m, nên không bao giờ có sự kiện `player_hit` với `by: "fall"`. Mọi trường khác trong `tuning` đều được game dùng thật, không có trường nào là `null`.

| Sự kiện | Điểm |
|---|---|
| Nhặt đom đóm | +10 |
| Thắp đèn | +100 |
| Mỗi Bóng Mực bị choáng | +20 |
| Thắng: mỗi giây còn lại | +1 |
| Thắng: mỗi flame còn lại | +50 |

Mọi giả định cho chỗ đề còn mơ hồ: [docs/notes/phase-1-assumptions.md](docs/notes/phase-1-assumptions.md).

## Test và bằng chứng

```bash
python3 -m unittest discover -s tests -t . -v   # unit test + test CLI
python3 tools/run_scenarios.py --phase phase-1  # scenario headless, chạy 2 lần để kiểm tra tất định
```

- Bằng chứng Phase 1: [docs/proof/phase-1/](docs/proof/phase-1/README.md)
- CI chạy cả hai lệnh trên Ubuntu và macOS mỗi lần push: [.github/workflows/ci.yml](.github/workflows/ci.yml)

## Cấu trúc

```text
lantern/sim.py          luật game, tất định, không phụ thuộc đồ họa
lantern/headless.py     CLI headless theo Test Contract
lantern/contract_io.py  kiểm tra file inputs/scenario (exit 2)
lantern/app.py          client 3D (Ursina), chỉ hiển thị trạng thái của sim
tests/                  unit test + tests/scenarios/*
tools/run_scenarios.py  chạy scenario, ghi bằng chứng
docs/notes/             giả định, nhật ký AI, retro
docs/proof/             bằng chứng từng phase
```

## Harness AI

- [AGENTS.md](AGENTS.md) (được `CLAUDE.md` nạp vào): lệnh, cấu trúc, quy tắc.
- Stop hook [.claude/settings.json](.claude/settings.json) → [.claude/hooks/stop_check.py](.claude/hooks/stop_check.py): chặn agent kết thúc khi test hoặc scenario đỏ.
- Skill [.claude/skills/verify-phase](.claude/skills/verify-phase/SKILL.md): quy trình chạy kiểm chứng và lưu bằng chứng trước khi gắn tag.

## Sáng tạo của tôi

*(sẽ bổ sung, sau khi phần lõi đã đúng)*
