# Credits

## Nhân vật, bối cảnh

Mây, Ông Đăng, Bóng Mực, Gió Lạc, Đảo Bến / Đảo Cau / Đảo Chuông là bản gốc của đề bài lab Day 12 (AI SDLC). Bảng màu chuẩn lấy từ Ticket-02.

## Đồ họa

Toàn bộ mô hình được dựng bằng code từ khối hình học cơ bản: hộp, cầu, trụ, nón (Ursina `Cylinder`/`Cone`, mesh tự sinh trong `lantern/client.py`). **Không dùng texture, model hay ảnh bên ngoài.** Font chữ là OpenSans, đi kèm thư viện Ursina (Apache License 2.0).

## Âm thanh

Mọi file trong `lantern/assets/sounds/*.wav` (nhạc nền và 12 hiệu ứng) được **tự sinh bằng code**: `tools/gen_sounds.py` dùng sóng sin/tam giác và nhiễu với Python stdlib. Phát hành cùng dự án theo giấy phép MIT. Không dùng âm thanh bên ngoài hay âm thanh do AI tạo.

## Thư viện

| Thư viện | Giấy phép | Dùng cho |
|---|---|---|
| [Ursina](https://www.ursinaengine.org/) 7.0.0 | MIT | client 3D |
| [Panda3D](https://www.panda3d.org/) 1.10 | BSD-3-Clause | renderer (Ursina dùng bên dưới) |
| [psutil](https://github.com/giampaolo/psutil) | BSD-3-Clause | đo RSS trong bench/soak |
| Python standard library | PSF | lõi game, headless, soak, sinh âm thanh |

## Công cụ AI

| Công cụ | Dùng để |
|---|---|
| Claude Code (Anthropic), model Claude Opus 5.5 | Viết code, test, scenario, tài liệu dưới sự điều phối và review của tác giả. Nhật ký chi tiết: [docs/notes/ai-log.md](docs/notes/ai-log.md) |

AI **không** được dùng để tạo hình ảnh hay âm thanh. Ảnh chụp trong `docs/img/` do chính game chụp ra (`--screenshot`).
