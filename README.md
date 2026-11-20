# Đảo Đèn Lồng

> **Video demo:** *(sẽ thêm ở Phase 4)* · Đề bài lab: [docs/lab/](docs/lab/README.md)

Game 3D góc nhìn thứ ba. Bạn điều khiển Mây, gom đom đóm để thắp lại các Đèn Lồng Lớn qua 3 Đêm (Đảo Bến, Đảo Cau, Đảo Chuông) trước bình minh, và né Bóng Mực cùng Gió Lạc trong sương đen.

**Trạng thái:** headless theo Test Contract **v1.2** (Ticket-03 "Đèn cạn dầu") đã xong cả 3 Đêm. Client 3D đang làm. Thay đổi: [CHANGELOG](CHANGELOG.md).

## Cài đặt và chạy (macOS / Linux, Python ≥ 3.10)

```bash
git clone <repo> && cd K5-L3A-DAY12-HoangLamMinh-2A202603566-AI-SDLC-Dao-Den-Long
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt   # chỉ bản 3D cần (ursina)
.venv/bin/python -m lantern.app                                                 # chơi
```

Dùng venv để tránh lỗi PEP 668 "externally-managed-environment" trên Python của Homebrew và Debian/Ubuntu mới.

Chế độ headless **không cần cài gì** (chỉ dùng Python stdlib):

```bash
python3 -m lantern.headless --seed 1 --night 1 --ticks 600   # --night 1|2|3 --out out.jsonl \
    [--scenario s.json] [--inputs i.json] [--snapshot-every 10]
```

Theo Test Contract v1.2, xem [game.contract.json](game.contract.json). Mã thoát: 0 chạy xong, 2 khi file inputs/scenario/tham số sai, 1 cho lỗi khác.

## Điều khiển

| Phím | Hành động |
|---|---|
| W A S D | Di chuyển (theo hướng camera) |
| Chuột | Xoay camera |
| Space | Nhảy |
| Shift | Lướt (14 m/s, 0.2 s, hồi 1.5 s) |
| Esc / P | Tạm dừng |
| E | Nạp ánh sáng vào đèn gần nhất |
| Q / chuột trái | Tỏa Sáng: choáng 2 s và đẩy lùi Bóng Mực trong 5 m, tốn 3 đom đóm, hồi 3 s |
| R | Chơi lại sau khi thắng/thua |

## Luật và cách tính điểm (Ticket-03)

- **Mục tiêu:** giữ đảo sáng tới bình minh (240/270/300 s). Lúc hết giờ phải có ≥ 60% số đèn đang sáng: 3/5, 4/6, 5/7.
- Thắp đèn lần đầu tốn 10 đom đóm. Đèn có dầu 100 và hao 1/s; hết dầu thì tắt. Thắp lại tốn 5. Nhấn E ở đèn đang sáng để châm dầu (+10 dầu mỗi đom đóm).
- Đèn có ≥ 30 dầu giữ vùng an toàn 6 m. Dưới 30, Bóng Mực vào hút dầu 5/s, và bạn dùng Tỏa Sáng hoặc lại gần để đuổi chúng.
- Sức chứa = 10 + 2 × số lần thắp thành công trong Đêm (tối đa 20).
- Bị Bóng Mực chạm: −1 Ngọn Lửa (có 3), rơi một nửa số đom đóm, bất tử 1.5 s. Hết Ngọn Lửa thì thua ngay.
- Gió Lạc (Đêm 2, 3) cướp 3 đom đóm. Bùa Gió tăng tốc trong 10 s. Rơi khỏi đảo thì mất 1 lửa và hết đom đóm.

| Sự kiện | Điểm |
|---|---|
| Mỗi đom đóm nạp vào đèn (thắp, thắp lại, châm dầu) | +5 |
| Thắp lần đầu / thắp lại | +100 / +40 |
| Mỗi Bóng Mực trúng Tỏa Sáng (đang hút dầu) | +5 (+15) |
| Bình minh khi thắng: mỗi đèn đang sáng | +50 + floor(dầu) |
| Bình minh khi thắng: mỗi Ngọn Lửa | +50 |

Trong `tuning`, mọi khóa đều được game dùng thật, không có trường nào là `null`. `fall_enabled: true`: rơi khỏi đảo bị phạt.

Giả định và tiêu chí nghiệm thu: [Phase 1](docs/notes/phase-1-assumptions.md) · [Phase 2](docs/notes/phase-2-spec.md) · [Phase 3 ADR](docs/adr/0001-lantern-fuel-and-dawn-win.md).

## Test và bằng chứng

```bash
python3 -m unittest discover -s tests -t . -v   # unit test + test CLI
python3 tools/run_scenarios.py --phase phase-3  # scenario headless, chạy 2 lần để kiểm tra tất định
```

- Bằng chứng: [Phase 1](docs/proof/phase-1/README.md) · [Phase 2](docs/proof/phase-2/README.md) · [Phase 3](docs/proof/phase-3/README.md)
- CI chạy cả hai lệnh trên Ubuntu và macOS mỗi lần push: [.github/workflows/ci.yml](.github/workflows/ci.yml)

## Cấu trúc

```text
lantern/sim.py          luật game, tất định, không phụ thuộc đồ họa
lantern/maps.py         bản đồ chuẩn 3 Đêm
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
