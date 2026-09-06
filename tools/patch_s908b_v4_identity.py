#!/usr/bin/env python3
import sys
from pathlib import Path

app = Path(sys.argv[1])

gradle = app / "app/build.gradle.kts"
text = gradle.read_text()
text = text.replace(
    'applicationId = "dev.busung.s25uroot.s908bofflinev3"',
    'applicationId = "dev.busung.s25uroot.s908bofflinev4"',
    1,
)
text = text.replace(
    'versionName = "0.2.65-s908b-offline-clean-v3"',
    'versionName = "0.2.65-s908b-offline-clean-v4"',
    1,
)
gradle.write_text(text)

repo = app / "app/src/main/java/dev/busung/s25uroot/PayloadRepository.kt"
r = repo.read_text()
r = r.replace("b0s-S908BXXSMGZB2-offline-clean-v3", "b0s-S908BXXSMGZB2-offline-clean-v4")
r = r.replace("GZB2 Offline Clean v3", "GZB2 Offline Clean v4")
repo.write_text(r)

for strings in (app / "app/src/main/res").glob("values*/strings.xml"):
    s = strings.read_text()
    s = s.replace("Root My Galaxy — S908B Offline Lab v3", "Root My Galaxy — S908B Offline Lab v4")
    strings.write_text(s)

print("lab_identity=v4")
