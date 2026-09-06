#!/usr/bin/env python3
import re
import sys
from pathlib import Path

app = Path(sys.argv[1])
assets = app / "app/src/main/assets/s908b"
payload = assets / "cve-2026-43499-app.cleanup.so"
ksu = assets / "ksud-r0s-S901BXXSNGZD7-kdp"
if not payload.is_file() or not ksu.is_file():
    raise SystemExit("offline assets missing")

payload_size = payload.stat().st_size
ksu_size = ksu.stat().st_size

# ---------------------------------------------------------------------------
# Offline S908B payload repository.  This keeps the lab build independent of
# the support feed while preserving the exact PR #272 payload/KSU pair.
# ---------------------------------------------------------------------------
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
        profileId = "b0s-S908BXXSMGZB2-offline-clean-v2",
        displayName = "Galaxy S22 Ultra SM-S908B | GZB2 Offline Clean v2",
        models = setOf("SM-S908B"),
        kernelVersions = setOf("5.10.237"),
        exploit = RemoteArtifact("asset://s908b/cve-2026-43499-app.cleanup.so", {payload_size}L),
        kernelSu = RemoteArtifact("asset://s908b/ksud-r0s-S901BXXSNGZD7-kdp", {ksu_size}L),
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
            "s908b/cve-2026-43499-app.cleanup.so",
            profile.exploit.size,
            File(directory, "cve-2026-43499-app.so"),
            context.getString(R.string.artifact_exploit),
            onProgress,
        )
        val kernelSu = copyAsset(
            "s908b/ksud-r0s-S901BXXSNGZD7-kdp",
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
        temporary.delete()
        context.assets.open(assetName).use {{ input ->
            FileOutputStream(temporary, false).use {{ output ->
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

# ---------------------------------------------------------------------------
# Installer runtime hygiene.
# Every new exploit run must start by deleting the paths that THIS RMG flow
# owns/reuses in /data/local/tmp.  A failure to clean is fatal: we never fall
# back to running against a stale cve-exp32/helper/payload/socket.
# ---------------------------------------------------------------------------
vm_path = app / "app/src/main/java/dev/busung/s25uroot/InstallViewModel.kt"
vm = vm_path.read_text()

needle = '''                val payloads = repository.download(profile) { appendLog("[*] $it") }
                appendLog(app.getString(R.string.log_download_verified))

                setPhase(InstallPhase.Exploiting, app.getString(R.string.status_exploit_running))'''
replacement = '''                val payloads = repository.download(profile) { appendLog("[*] $it") }
                appendLog(app.getString(R.string.log_download_verified))

                prepareFreshRuntimeWorkspace()

                setPhase(InstallPhase.Exploiting, app.getString(R.string.status_exploit_running))'''
if needle not in vm:
    raise SystemExit("install() insertion point not found")
vm = vm.replace(needle, replacement, 1)

insert_before = '''    private suspend fun executeExploit(payload: File) {'''
cleanup_function = '''    private suspend fun prepareFreshRuntimeWorkspace() {
        require(shizukuEnabled()) {
            "Esta build de laboratório exige Shizuku para garantir um workspace temporário limpo."
        }
        appendLog("[*] ── Preparando ambiente limpo ──")
        appendLog("[*] Removendo arquivos temporários antigos do Root My Galaxy")
        val cleanup = ShizukuController.exec(
            arrayOf("rm", "-f", "--", *RMG_TEMP_PATHS),
        )
        val captured = StringBuilder()
        while (cleanup.isAlive) {
            drainProcessOutput(cleanup, captured)
            delay(50.milliseconds)
        }
        drainProcessOutput(cleanup, captured)
        val exitCode = cleanup.waitFor()
        require(exitCode == 0) {
            "Falha ao limpar o workspace temporário" +
                captured.toString().trim().takeIf(String::isNotBlank)?.let { ": $it" }.orEmpty()
        }
        val leftovers = RMG_TEMP_PATHS.filter { File(it).exists() }
        require(leftovers.isEmpty()) {
            "Arquivos temporários antigos ainda existem: ${leftovers.joinToString()}"
        }
        appendLog("[+] Workspace temporário limpo")
        appendLog("[+] Payload, helper e KernelSU serão regravados nesta sessão")
    }

'''
if insert_before not in vm:
    raise SystemExit("executeExploit insertion point not found")
vm = vm.replace(insert_before, cleanup_function + insert_before, 1)

# Verify each newly staged file instead of trusting a successful write call.
stage_old = '''        try {
            ShizukuController.writeFile(target, mode, source.inputStream())
        } catch (error: Throwable) {
            throw IllegalStateException(
                app.getString(R.string.error_shizuku_stage, target, error.message.orEmpty()),
                error,
            )
        }
        return staged
    }'''
stage_new = '''        try {
            ShizukuController.writeFile(target, mode, source.inputStream())
        } catch (error: Throwable) {
            throw IllegalStateException(
                app.getString(R.string.error_shizuku_stage, target, error.message.orEmpty()),
                error,
            )
        }
        require(stagedFileIsCurrent(staged, source)) {
            "Arquivo temporário não corresponde à cópia desta sessão: $target"
        }
        return staged
    }'''
if stage_old not in vm:
    raise SystemExit("shizukuStage body not found")
vm = vm.replace(stage_old, stage_new, 1)

const_anchor = '''        private const val SHIZUKU_KSUD_STAGE_PATH = "/data/local/tmp/.ksud-stage"
'''
const_block = '''        private const val SHIZUKU_KSUD_STAGE_PATH = "/data/local/tmp/.ksud-stage"
        private val RMG_TEMP_PATHS = arrayOf(
            SHIZUKU_LOG_PATH,
            SHIZUKU_HELPER_PATH,
            SHIZUKU_PAYLOAD_PATH,
            SHIZUKU_KSUD_PATH,
            SHIZUKU_KSUD_STAGE_PATH,
            "/data/local/tmp/cve-exp32",
            "/data/local/tmp/temp_su.sock",
        )
'''
if const_anchor not in vm:
    raise SystemExit("temp constants anchor not found")
vm = vm.replace(const_anchor, const_block, 1)
vm_path.write_text(vm)

# ---------------------------------------------------------------------------
# Prettier live log.  Keep the raw text unchanged for exports/history; only
# the Compose presentation is annotated/colorized.  This avoids hiding useful
# exploit diagnostics while making milestones and failures much easier to see.
# ---------------------------------------------------------------------------
activity_path = app / "app/src/main/java/dev/busung/s25uroot/InstallActivity.kt"
activity = activity_path.read_text()

import_anchor = '''import androidx.compose.ui.platform.LocalView
'''
imports = '''import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
'''
if import_anchor not in activity:
    raise SystemExit("InstallActivity import anchor not found")
activity = activity.replace(import_anchor, imports, 1)

old_pattern = re.compile(
    r'@Composable\nprivate fun InstallerLog\([\s\S]*?\n}\n\n@Composable\nprivate fun installPhaseDetail',
)
new_log = r'''@Composable
private fun InstallerLog(
    output: String,
    modifier: Modifier,
    scrollState: androidx.compose.foundation.ScrollState,
) {
    val colors = MaterialTheme.colorScheme
    val preparing = stringResource(R.string.install_preparing)
    val renderedLog = remember(
        output,
        preparing,
        colors.primary,
        colors.secondary,
        colors.tertiary,
        colors.error,
        colors.onSurfaceVariant,
    ) {
        buildInstallerLogText(
            source = output.ifBlank { preparing },
            success = colors.primary,
            retry = colors.tertiary,
            info = colors.onSurfaceVariant,
            failure = colors.error,
            accent = colors.secondary,
        )
    }
    val failed = output.contains("kernel panic", ignoreCase = true) ||
        output.contains("failed after", ignoreCase = true) ||
        output.contains("instalação falhou", ignoreCase = true)
    val completed = output.contains("exploit completed", ignoreCase = true) ||
        output.contains("KernelSU ativo", ignoreCase = true) ||
        output.contains("Instalação completa", ignoreCase = true)
    val badgeText = when {
        failed -> "ERRO"
        completed -> "OK"
        else -> "LIVE"
    }
    val badgeColor = when {
        failed -> colors.error
        completed -> colors.primary
        else -> colors.tertiary
    }

    Card(
        modifier = modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.large,
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = stringResource(R.string.install_live_progress),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        text = "Root My Galaxy • console da execução",
                        style = MaterialTheme.typography.bodySmall,
                        color = colors.onSurfaceVariant,
                    )
                }
                Surface(
                    shape = CircleShape,
                    color = badgeColor.copy(alpha = 0.14f),
                    contentColor = badgeColor,
                ) {
                    Text(
                        text = badgeText,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }

            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f),
                shape = MaterialTheme.shapes.medium,
                color = colors.surfaceContainerLowest,
                tonalElevation = 1.dp,
            ) {
                Text(
                    text = renderedLog,
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(scrollState)
                        .padding(horizontal = 14.dp, vertical = 12.dp),
                    fontFamily = FontFamily.Monospace,
                    fontSize = 11.5.sp,
                    lineHeight = 17.sp,
                    color = colors.onSurfaceVariant,
                )
            }
        }
    }
}

private fun buildInstallerLogText(
    source: String,
    success: Color,
    retry: Color,
    info: Color,
    failure: Color,
    accent: Color,
): AnnotatedString = buildAnnotatedString {
    val lines = source.replace("\r", "").lines()
    lines.forEachIndexed { index, line ->
        val lower = line.lowercase()
        val importantSuccess =
            "phys_slot_match" in lower ||
                "done=1 root=1" in lower ||
                "uid=2000->0" in lower ||
                "exploit completed" in lower ||
                "kernelsu ativo" in lower ||
                "instalação completa" in lower ||
                "workspace temporário limpo" in lower
        val expectedRetry =
            "phys_slot_no_match" in lower ||
                "failed status=70" in lower ||
                "cache gate failed" in lower ||
                "read64 done ok=0" in lower
        val hardFailure =
            "kernel panic" in lower ||
                "failed after" in lower ||
                "instalação falhou" in lower ||
                "execution failed" in lower ||
                "timeout" in lower

        val style = when {
            hardFailure || line.startsWith("[!]") -> SpanStyle(
                color = failure,
                fontWeight = FontWeight.Bold,
            )
            importantSuccess -> SpanStyle(
                color = success,
                fontWeight = FontWeight.Bold,
            )
            expectedRetry -> SpanStyle(color = retry)
            line.startsWith("[+]") -> SpanStyle(color = success)
            line.startsWith("[-]") -> SpanStyle(color = accent)
            line.startsWith("[*]") -> SpanStyle(color = info)
            else -> SpanStyle(color = info)
        }
        pushStyle(style)
        append(line)
        pop()
        if (index != lines.lastIndex) append('\n')
    }
}

@Composable
private fun installPhaseDetail'''
activity, count = old_pattern.subn(new_log, activity, count=1)
if count != 1:
    raise SystemExit(f"InstallerLog replacement count={count}")
activity_path.write_text(activity)

# ---------------------------------------------------------------------------
# Distinct lab package/name so it can coexist with Preview and official app.
# ---------------------------------------------------------------------------
gradle = app / "app/build.gradle.kts"
gradle_text = gradle.read_text()
gradle_text = gradle_text.replace(
    'applicationId = "dev.busung.s25uroot"',
    'applicationId = "dev.busung.s25uroot.s908bofflinev2"',
    1,
)
gradle_text = gradle_text.replace(
    'versionName = "0.2.65"',
    'versionName = "0.2.65-s908b-offline-clean-v2"',
    1,
)
gradle.write_text(gradle_text)

labels_patched = 0
for strings in (app / "app/src/main/res").glob("values*/strings.xml"):
    source = strings.read_text()
    patched, count = re.subn(
        r'(<string name="app_name">).*?(</string>)',
        r'\1Root My Galaxy — S908B Offline Lab v2\2',
        source,
        count=1,
    )
    if count:
        strings.write_text(patched)
        labels_patched += 1
if not labels_patched:
    raise SystemExit("app_name not found")

print(f"payload_size={payload_size}")
print(f"ksu_size={ksu_size}")
print(f"labels_patched={labels_patched}")
print("runtime_cleanup=enabled")
print("log_ui=annotated-terminal")
