#!/usr/bin/env python3
import re
import sys
from pathlib import Path

app = Path(sys.argv[1])
payload = app / "app/src/main/assets/s908b-sarab-1bfc3ae.so"
payload_size = payload.stat().st_size

repo = app / "app/src/main/java/dev/busung/s25uroot/PayloadRepository.kt"
repo.write_text(f'''package dev.busung.s25uroot

import android.content.Context
import android.system.Os
import java.io.File
import java.io.FileOutputStream

data class VerifiedPayloads(
    val profile: TargetProfile,
    val exploit: File,
    val kernelSu: File,
)

class PayloadRepository(private val context: Context) {{
    private val localProfile = TargetProfile(
        profileId = "b0s-S908BXXSMGZB2-sarab-1bfc3ae",
        displayName = "Galaxy S22 Ultra SM-S908B | Sarab 1bfc3ae A/B",
        models = setOf("SM-S908B"),
        kernelVersions = setOf("5.10.237"),
        exploit = RemoteArtifact("asset://s908b-sarab-1bfc3ae.so", {payload_size}L),
        kernelSu = RemoteArtifact("asset://ksud-r0s-S901BXXSNGZD7-kdp", 4621280L),
    )

    fun loadTargets(): List<TargetProfile> = listOf(localProfile)

    fun resolveTarget(snapshot: DeviceSnapshot): TargetProfile =
        localProfile.takeIf {{ it.matches(snapshot) }}
            ?: error(context.getString(R.string.repo_no_profile))

    fun resolveTarget(profileId: String): TargetProfile =
        localProfile.takeIf {{ it.profileId == profileId }}
            ?: error(context.getString(R.string.repo_profile_missing, profileId))

    fun download(profile: TargetProfile, onProgress: (String) -> Unit): VerifiedPayloads {{
        val directory = File(context.filesDir, "payloads/" + profile.profileId).apply {{ mkdirs() }}
        val exploit = copyAsset(
            "s908b-sarab-1bfc3ae.so",
            profile.exploit.size,
            File(directory, "cve-2026-43499-app.so"),
            context.getString(R.string.artifact_exploit),
            onProgress,
        )
        val kernelSu = copyAsset(
            "ksud-r0s-S901BXXSNGZD7-kdp",
            profile.kernelSu.size,
            File(directory, "ksud-s25u-kdp"),
            context.getString(R.string.artifact_kernelsu),
            onProgress,
        )
        Os.chmod(exploit.absolutePath, 0b100100100)
        Os.chmod(kernelSu.absolutePath, 0b100100100)
        return VerifiedPayloads(profile, exploit, kernelSu)
    }}

    private fun copyAsset(
        assetName: String,
        expectedSize: Long,
        destination: File,
        label: String,
        onProgress: (String) -> Unit,
    ): File {{
        onProgress(context.getString(R.string.repo_downloading, label))
        val temporary = File(destination.parentFile, destination.name + ".part")
        context.assets.open(assetName).use {{ input ->
            FileOutputStream(temporary).use {{ output ->
                input.copyTo(output)
                output.fd.sync()
            }}
        }}
        require(temporary.length() == expectedSize) {{ context.getString(R.string.repo_size_mismatch, label) }}
        if (destination.exists()) destination.delete()
        require(temporary.renameTo(destination)) {{ context.getString(R.string.repo_finalize_failed, label) }}
        onProgress(context.getString(R.string.repo_verified, label))
        return destination
    }}
}}
''')

gradle = app / "app/build.gradle.kts"
text = gradle.read_text()
text = text.replace(
    'applicationId = "dev.busung.s25uroot"',
    'applicationId = "dev.busung.s25uroot.sarabtest"',
    1,
)
text = text.replace(
    'versionName = "0.2.65"',
    'versionName = "0.2.65-sarab-1bfc3ae"',
    1,
)
gradle.write_text(text)

changed = 0
for strings in (app / "app/src/main/res").glob("values*/strings.xml"):
    source = strings.read_text()
    patched, count = re.subn(
        r'(<string name="app_name">).*?(</string>)',
        r'\1Root My Galaxy — Sarab A/B\2',
        source,
        count=1,
    )
    if count:
        strings.write_text(patched)
        changed += 1

if not changed:
    raise SystemExit("app_name not found")

print(f"payload_size={payload_size}")
print(f"labels_patched={changed}")
