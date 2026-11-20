# Bằng chứng Phase 3 (Contract v1.2, Ticket-03)

Chạy lại ở tag `phase-3`:

```bash
python3 -m unittest discover -s tests -t . -v     # 96 test (24 test mới trong tests/test_phase3.py)
python3 tools/run_scenarios.py --phase phase-3    # 25 scenario, mỗi cái chạy 2 lần và so từng byte
```

Bảng scenario: [scenarios.md](scenarios.md). Quyết định thiết kế: [ADR 0001](../../adr/0001-lantern-fuel-and-dawn-win.md). Breaking changes: [CHANGELOG](../../../CHANGELOG.md).

| Mục Ticket-03 | Tiêu chí nghiệm thu | Bằng chứng | Kết quả |
|---|---|---|---|
| 1. Nhiên liệu | Thắp → 100. Hao 1/s. ≤ 0 thì tắt (`lantern_out`, deposited 0, ever_lit). Châm dầu `min(mang, ceil((100−f)/10))`. Đèn đầy không được chọn. Thắp lại tốn 5 | `Fuel` (8 test), scenario 19, 20, 21 | Đạt |
| 2. Hút dầu | fuel < 30 mất vùng an toàn, đúng 30 vẫn còn. `wander` đi tới đèn yếu → `drain` trong 2 m. Hút 5/s, cộng dồn nhiều con. `fuel_drain` mỗi 60 tick. Thoát `drain` → chase (6 m), stunned, wander (đèn tắt / ≥ 30). Châm lên ≥ 30 thì đẩy Bóng Mực ra mép | `LowFuelAndDrain` (8 test), scenario 22 (khớp tính tay: dầu 15.0 / 9.0 / 3.0 ở tick 301 / 361 / 421, tắt ở tick 451) | Đạt |
| 3. Luật thắng | 240/270/300 s. Ngưỡng 3/5, 4/6, 5/7 → `dawn_survived`, thiếu thì `dawn`. Hết lửa ở tick cuối vẫn là `no_flames`. Không thắng sớm | `WinRule`, `test_all_lit_no_longer_wins_early`, scenario 03, 23, 24 | Đạt |
| 4. Sức chứa | 10 + 2 × số lần thắp, tối đa 20. Đèn đặt sẵn không tính | `Capacity` (4 test), scenario 25 | Đạt |
| 5. Điểm | +5 mỗi đom đóm nạp, +100 / +40, pulse +5 / +15 (`drain`), bình minh 50 + floor(fuel) cho mỗi đèn và 50 cho mỗi lửa | `test_refuel_formula`, `test_relight_*`, `test_pulse_draining_shade_scores_15`, `test_dawn_score` | Đạt |
| 6. Chế độ mù màu | Đổi màu, biểu tượng ⚠, đèn xẹp / rách | Client 3D | **Chưa đạt** (chưa có client 3D) |
| 7. Contract v1.2 | Tuning, snapshot, scenario, sự kiện mới | Các test trên + `test_cli.py` | Đạt |
| Regression Phase 1–2 | Test không bị thay vẫn đạt | 72 test cũ + scenario 01–18 | Đạt (các thay đổi có lý do trong [CHANGELOG](../../../CHANGELOG.md)) |
