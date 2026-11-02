# -*- coding: utf-8 -*-
"""Парсер NTRIP SOURCETABLE (строки STR;)."""


class SourcetableParser:
    @staticmethod
    def parse(raw_text: str) -> list:
        mountpoints = []
        for line in raw_text.splitlines():
            line = line.strip()
            if line.startswith("STR;"):
                parts = line.split(";")
                if len(parts) >= 10:
                    try:
                        mp = {
                            "mountpoint": parts[1],
                            "identifier": parts[2] if len(parts) > 2 else "",
                            "format": parts[3] if len(parts) > 3 else "",
                            "format_details": parts[4] if len(parts) > 4 else "",
                            "carrier": parts[5] if len(parts) > 5 else "",
                            "nav_system": parts[6] if len(parts) > 6 else "",
                            "network": parts[7] if len(parts) > 7 else "",
                            "country": parts[8] if len(parts) > 8 else "",
                            "latitude": float(parts[9]) if len(parts) > 9 and parts[9] else 0.0,
                            "longitude": float(parts[10]) if len(parts) > 10 and parts[10] else 0.0,
                            "nmea": parts[11] if len(parts) > 11 else "",
                            "solution": parts[12] if len(parts) > 12 else "",
                            "generator": parts[13] if len(parts) > 13 else "",
                            "compression": parts[14] if len(parts) > 14 else "",
                            "authentication": parts[15] if len(parts) > 15 else "",
                            "fee": parts[16] if len(parts) > 16 else "",
                            "bitrate": parts[17] if len(parts) > 17 else "",
                        }
                        mountpoints.append(mp)
                    except (ValueError, IndexError) as e:
                        print(f"Ошибка парсинга строки STR: {e}")
        return mountpoints
