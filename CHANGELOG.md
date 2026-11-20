# Changelog

## [v1.0.0 / phase-4] Contract v1.3: "Bình minh" (Ticket-04)

### Thêm
- **Client 3D (Ursina)** hoàn chỉnh. Bù toàn bộ phần GUI còn thiếu của Phase 1–3: menu, giới thiệu Đêm (Ông Đăng), chuỗi 3 Đêm, Bình Minh, tạm dừng, cài đặt có lưu, âm thanh tự sinh, HUD đầy đủ, mũi tên chỉ đèn và Bóng Mực, bảng màu chuẩn, chế độ mù màu, thanh dầu nhấp nháy 1 Hz.
- **Benchmark** `lantern.app --bench` (cảnh chuẩn 200 Bóng Mực / 100 đom đóm, camera bay vòng) → `bench.json`.
- **Soak** `lantern.soak` (10 Đêm trong cùng một tiến trình) → `soak.json`.
- **Bảng xếp hạng cục bộ** top 10 (lưu đĩa, hỗ trợ tên tiếng Việt), `--export-leaderboard`.
- **Dễ tiếp cận**: đổi mọi phím (báo trùng, khôi phục mặc định), phụ đề và chỉ báo hình ảnh, giảm chuyển động, chữ ≥ 18 px và tùy chọn ×1.25.
- `game.contract.json`: `contract_version` 1.3, `bench_cmd`, `soak_cmd`. Sim có cờ `bench` (mặc định tắt, không đổi output headless).
- LICENSE (MIT), CREDITS.md, retro, ảnh chụp trong `docs/img/`.

### Hiệu năng
- Từ 22.8 lên 104–120 avg fps trong cảnh bench: mesh gộp bằng màu đỉnh, `RigidBodyCombiner`, `flattenStrong`, chỉ cập nhật HUD khi đổi, `gc.freeze()`.

### Breaking
- Không có thay đổi luật. `requirements.txt` thêm `psutil`.

## [phase-3] Contract v1.2: "Đèn cạn dầu" (Ticket-03)

### ⚠ Breaking changes

- **Không còn thắng sớm.** Thắp hết đèn không kết thúc Đêm. `game_over.reason` không còn `all_lit`. Thắng giờ là `dawn_survived`: còn sống khi hết giờ và có ≥ ceil(0.6 × số đèn) đèn đang sáng.
- **Đèn tắt được.** Đèn có `fuel` 0–100, hao 1/s. Hết dầu thì `lit: false`, `deposited: 0`, có sự kiện `lantern_out`.
- **Tương tác với đèn đã sáng** giờ là châm dầu (sự kiện `refuel`). Trước đây đèn sáng không nhận thêm đom đóm.
- **Vùng an toàn** mất khi `fuel < 30`, nên Bóng Mực có thể vào và hút dầu (trạng thái mới `drain`).
- **Thời lượng Đêm** đổi từ 300/330/360 s thành **240/270/300 s**.
- **Điểm:** +5 mỗi đom đóm nạp (trước +10). Thắp lại +40. Pulse trúng con đang `drain` +15. Bình minh: +50 + floor(fuel) cho mỗi đèn sáng, +50 cho mỗi Ngọn Lửa. **Bỏ thưởng thời gian.**
- **Sức chứa** = 10 + 2 × số lần thắp thành công, tối đa 20.
- `lantern_lit.data` có thêm `relight`. Snapshot của đèn có thêm `fuel`, `ever_lit`, `relit_count`. `player` có thêm `capacity`.

### Thêm

- Tuning: `fuel_max`, `fuel_decay_per_s`, `fuel_per_mote`, `relight_cost`, `win_ratio`, `drain_per_s`, `low_fuel_threshold`, `capacity_max`. Score: `per_relight`, `per_drain_stun`, `per_lit_at_dawn`.
- Scenario: `lanterns[].fuel`, `lanterns[].ever_lit`, `player.successful_lights`, `shades[].target_lantern_id`.
- Sự kiện: `refuel`, `lantern_out`, `fuel_drain`.
- Quyết định thiết kế: [docs/adr/0001-lantern-fuel-and-dawn-win.md](docs/adr/0001-lantern-fuel-and-dawn-win.md).

### Test bị luật mới làm sai (đã sửa, không skip)

| Test | Thay đổi |
|---|---|
| `test_win_all_lit_and_bonus` | Thay bằng `test_all_lit_no_longer_wins_early` |
| `test_deposit_and_light` | `relight: false`; điểm 10 × 5 + 100 |
| `test_contract_file` | contract 1.2 |
| scenario 01 | điểm 200 → 150 |
| scenario 03 | trước: thắng `all_lit` → giờ: vẫn `playing` sau khi thắp đủ |
| scenario 17, 18 | full night 16.200 / 18.000 tick |

## [phase-2] Contract v1.1 (Ticket-02)

- Số liệu chuẩn, 3 Đêm, lướt, rơi khỏi đảo, Gió Lạc, Bùa Gió, tạm dừng, gió mạnh. Xem [docs/notes/phase-2-spec.md](docs/notes/phase-2-spec.md).
- Breaking: điểm tính khi nạp (không tính khi nhặt); dòng đầu output là `night_start`; tên trạng thái Bóng Mực chuẩn.

## [phase-1] Contract v1.0

- Lõi headless, Đêm 1, test và harness.
