#!/usr/bin/env python3
import re
import sys
from pathlib import Path

app = Path(sys.argv[1])
activity_path = app / "app/src/main/java/dev/busung/s25uroot/InstallActivity.kt"
activity = activity_path.read_text()

pattern = re.compile(
    r'private fun buildInstallerLogText\([\s\S]*?\n}\n\n@Composable\nprivate fun installPhaseDetail',
)

replacement = r'''private fun buildInstallerLogText(
    source: String,
    success: Color,
    retry: Color,
    info: Color,
    failure: Color,
    accent: Color,
): AnnotatedString = buildAnnotatedString {
    val rawLines = source.replace("\r", "").lines()
    val summary = mutableListOf<Pair<String, SpanStyle>>()
    val seen = mutableSetOf<String>()
    var currentAttempt: String? = null

    fun addOnce(key: String, text: String, style: SpanStyle) {
        if (seen.add(key)) summary += text to style
    }

    fun replaceAttempt(text: String, style: SpanStyle) {
        val key = "attempt:${currentAttempt ?: text}"
        val index = summary.indexOfLast { it.first.startsWith("• Tentativa ") || it.first.startsWith("↻ Tentativa ") }
        if (index >= 0 && currentAttempt != null && summary[index].first.contains(currentAttempt!!)) {
            summary[index] = text to style
        } else {
            addOnce(key, text, style)
        }
    }

    rawLines.forEach { line ->
        val lower = line.lowercase()

        when {
            "permissão do shizuku concedida" in lower ->
                addOnce("shizuku", "✓ Shizuku pronto", SpanStyle(color = success, fontWeight = FontWeight.SemiBold))

            "perfil de suporte:" in lower -> {
                val profile = line.substringAfter("Perfil de suporte:", "").trim()
                addOnce("profile", "✓ Perfil carregado: $profile", SpanStyle(color = success))
            }

            "download do payload completo" in lower ->
                addOnce("payloads", "✓ Payload e KernelSU verificados", SpanStyle(color = success))

            "workspace temporário limpo" in lower ->
                addOnce("workspace", "✓ Ambiente temporário limpo", SpanStyle(color = success, fontWeight = FontWeight.SemiBold))

            "payload, helper e kernelsu serão regravados" in lower ->
                addOnce("restage", "✓ Arquivos da sessão serão regravados do zero", SpanStyle(color = success))

            "socket bootstrap antigo detectado" in lower ->
                addOnce("old-socket", "i Socket antigo detectado; o helper root cuidará dele", SpanStyle(color = info))

            "rodando exploit de kernel" in lower ->
                addOnce("exploit-start", "• Iniciando exploit de kernel", SpanStyle(color = accent, fontWeight = FontWeight.SemiBold))

            "exploit attempt=" in lower -> {
                val match = Regex("attempt=(\\d+/\\d+)").find(line)
                currentAttempt = match?.groupValues?.getOrNull(1)
                currentAttempt?.let {
                    addOnce("attempt:$it", "• Tentativa $it", SpanStyle(color = info))
                }
            }

            "phys_slot_no_match" in lower -> {
                currentAttempt?.let {
                    replaceAttempt("↻ Tentativa $it — slot físico não encontrado, repetindo", SpanStyle(color = retry))
                }
            }

            "slide-kaslr-ok" in lower ->
                addOnce("kaslr:${currentAttempt ?: ""}", "✓ KASLR resolvido", SpanStyle(color = success))

            "phys_slot_match" in lower -> {
                val slot = Regex("slot=(\\d+)").find(line)?.groupValues?.getOrNull(1)
                addOnce(
                    "phys-slot",
                    if (slot != null) "✓ Slot físico encontrado: $slot" else "✓ Slot físico encontrado",
                    SpanStyle(color = success, fontWeight = FontWeight.SemiBold),
                )
            }

            "pipe physrw" in lower && "done=1" in lower ->
                addOnce("physrw", "✓ Leitura/escrita física confirmada", SpanStyle(color = success))

            "root umh result" in lower && "socket=1" in lower ->
                addOnce("root-socket", "✓ Bootstrap root estabelecido", SpanStyle(color = success))

            "uid=2000->0" in lower ->
                addOnce("uid-root", "✓ Root adquirido (uid 2000 → 0)", SpanStyle(color = success, fontWeight = FontWeight.Bold))

            "exploit completed attempt=" in lower -> {
                val attempt = Regex("attempt=(\\d+/\\d+)").find(line)?.groupValues?.getOrNull(1)
                addOnce(
                    "exploit-complete",
                    if (attempt != null) "✓ Exploit concluído na tentativa $attempt" else "✓ Exploit concluído",
                    SpanStyle(color = success, fontWeight = FontWeight.Bold),
                )
            }

            "canal de controle do kernelsu verificado" in lower ->
                addOnce("ksu-control", "✓ Canal de controle do KernelSU verificado", SpanStyle(color = success))

            line.trim().equals("[*] KernelSU ativo", ignoreCase = true) ||
                line.trim().equals("[+] KernelSU ativo", ignoreCase = true) ->
                addOnce("ksu-active", "✓ KernelSU ativo", SpanStyle(color = success, fontWeight = FontWeight.Bold))

            "socket bootstrap não pôde ser removido" in lower ->
                addOnce("socket-warning", "! Aviso: o socket bootstrap não foi removido automaticamente", SpanStyle(color = retry))

            "kernel panic" in lower ->
                addOnce("panic", "✕ Kernel panic detectado", SpanStyle(color = failure, fontWeight = FontWeight.Bold))

            "failed after" in lower ->
                addOnce("attempts-failed", "✕ Todas as tentativas do exploit falharam", SpanStyle(color = failure, fontWeight = FontWeight.Bold))

            "instalação falhou" in lower ->
                addOnce("install-failed", "✕ Instalação falhou — exporte o log técnico para detalhes", SpanStyle(color = failure, fontWeight = FontWeight.Bold))

            "instalação completa" in lower ->
                addOnce("install-complete", "✓ Instalação completa", SpanStyle(color = success, fontWeight = FontWeight.Bold))
        }
    }

    if (summary.isEmpty()) {
        summary += "• Preparando execução…" to SpanStyle(color = info)
    }

    summary.forEachIndexed { index, (text, style) ->
        pushStyle(style)
        append(text)
        pop()
        if (index != summary.lastIndex) append('\n')
    }
}

@Composable
private fun installPhaseDetail'''

activity, count = pattern.subn(lambda _m: replacement, activity, count=1)
if count != 1:
    raise SystemExit(f"compact log replacement count={count}")

activity = activity.replace(
    'text = "Root My Galaxy • console da execução",',
    'text = "Resumo da execução • log técnico completo continua salvo",',
    1,
)
activity_path.write_text(activity)

# Distinct package/version/name so this v4 can coexist with the earlier lab APKs.
gradle = app / "app/build.gradle.kts"
gradle_text = gradle.read_text()
gradle_text = gradle_text.replace(
    'applicationId = "dev.busung.s25uroot.s908bofflinev2"',
    'applicationId = "dev.busung.s25uroot.s908bofflinev4"',
    1,
)
gradle_text = gradle_text.replace(
    'versionName = "0.2.65-s908b-offline-clean-v2"',
    'versionName = "0.2.65-s908b-offline-clean-v4"',
    1,
)
gradle.write_text(gradle_text)

labels = 0
for strings in (app / "app/src/main/res").glob("values*/strings.xml"):
    text = strings.read_text()
    patched, count = re.subn(
        r'(<string name="app_name">).*?(</string>)',
        r'\1Root My Galaxy — S908B Offline Lab v4\2',
        text,
        count=1,
    )
    if count:
        strings.write_text(patched)
        labels += 1

print("compact_log_ui=enabled")
print(f"labels_patched_v4={labels}")
