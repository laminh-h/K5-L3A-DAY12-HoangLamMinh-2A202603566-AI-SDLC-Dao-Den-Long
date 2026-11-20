# Bằng chứng Phase 1

Chạy lại tất cả ở tag `phase-1`:

```bash
python3 -m unittest discover -s tests -t . -v     # 34 test
python3 tools/run_scenarios.py --phase phase-1    # tạo lại scenarios.md và runs/*.jsonl
```

Bảng kết quả scenario do script sinh tự động: [scenarios.md](scenarios.md). File output gốc nằm trong [runs/](runs/).

## Truy vết từ yêu cầu tới bằng chứng

Tiêu chí R1–R12 lấy từ [phase-1-assumptions.md](../../notes/phase-1-assumptions.md#4-tiêu-chí-nghiệm-thu).

| Yêu cầu | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| R1 di chuyển, yaw, chuẩn hóa, nhảy | Unit test | `tests/test_rules.py::Movement` | Đạt |
| R2 nhặt đom đóm, bán kính, sức chứa | Unit test + scenario | `Motes`, `runs/01_pickup_deposit_light.jsonl` | Đạt |
| R3 nạp và thắp đèn, kích hoạt theo cạnh nút | Unit test + scenario | `Lanterns`, scenario 01 | Đạt |
| R4 thắng `all_lit` + thưởng | Unit test + scenario | `test_win_all_lit_and_bonus`, scenario 03 | Đạt |
| R5 Bóng Mực đuổi, chạm, rơi đom đóm, bất tử | Unit test + scenario | `ShadesAndPulse`, scenario 02 (chạm ở tick 271 sau khi hết choáng) | Đạt |
| R6 thua `no_flames` / `dawn` | Unit test + scenario | `test_lose_no_flames`, `Dawn`, scenario 04, 05 | Đạt |
| R7 pulse: choáng, đẩy, chi phí, hồi chiêu, thời lượng | Unit test + scenario | `test_pulse_*`, `test_stun_duration`, scenario 02 | Đạt |
| R8 vùng an toàn quanh đèn đã thắp | Unit test (600 tick, mọi snapshot) | `test_safe_radius_blocks_shade` | Đạt |
| R9 mô hình tick, snapshot, dòng `end` | Unit test | `TickModel` | Đạt |
| R10 tất định | Chạy 2 lần, so từng byte | `test_deterministic_files`, `run_scenarios.py` (mọi scenario), CI | Đạt |
| R11 mã thoát 2 | Gọi CLI thật bằng subprocess | `tests/test_cli.py` | Đạt |
| R12 bản 3D chơi được + HUD + chơi lại | Chơi thử + ảnh chụp | *(đang làm)* | **Chưa đạt** (chưa có client 3D) |
