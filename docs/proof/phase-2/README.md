# Bằng chứng Phase 2 (Contract v1.1)

Chạy lại ở tag `phase-2`:

```bash
python3 -m unittest discover -s tests -t . -v     # 72 test, ~5 s
python3 tools/run_scenarios.py --phase phase-2    # 18 scenario, mỗi cái chạy 2 lần và so từng byte
```

Bảng scenario do script sinh: [scenarios.md](scenarios.md). Output gốc: [runs/](runs/).

## Truy vết yêu cầu (ID theo [phase-2-spec.md](../../notes/phase-2-spec.md#3-tiêu-chí-nghiệm-thu-phần-3-và-các-luật-chính))

| ID | Kết quả | Bằng chứng |
|---|---|---|
| P2-1 … P2-16 | Đạt | Unit test tương ứng trong `tests/test_rules.py` + scenario 01–16 |
| P2-17 hiệu năng headless | Đạt | Đêm 3 đủ 21.600 tick, 10 Bóng Mực: 1.9 s trong tiến trình, 2.3 s tính cả khởi động (Windows 10, Python 3.13). Scenario 18 kiểm `end.ticks = 21600` |
| Regression Phase 1 | Đạt | Scenario 01–06 vẫn chạy với số chuẩn; các thay đổi kỳ vọng có lý do trong spec mục 4 |
| P2-18 chuỗi 3 Đêm, menu, pause UI, cài đặt, âm thanh, HUD, bảng màu, ≥ 30 FPS | **Chưa đạt** | Chưa có client 3D. Đã chọn ưu tiên Test Contract |

## Lỗi phát hiện khi kiểm chứng

- Runner headless dừng khi `state != "playing"`, nên dừng luôn khi game đang `paused`. Đã sửa thành chỉ dừng khi `won`/`lost`, và có `test_pause_freezes_sim` kiểm lại.
- Các scenario "full night" ban đầu thua sớm ở tick 1140–2018, nên chưa chứng minh được yêu cầu hiệu năng. Đã sửa thành chạy với 999 flames và kiểm `end_ticks`.
