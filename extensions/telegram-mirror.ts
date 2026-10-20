import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

// Mirrors every terminal Pi exchange (question + final answer) to the Telegram "Pi" group.
// Runs started by the Telegram bridge set PI_TG_BRIDGE=1 and are skipped, since the bridge already replies there.
const textOf = (c: any): string =>
	typeof c === "string" ? c : (c || []).filter((p: any) => p.type === "text").map((p: any) => p.text).join("\n");

export default function (pi: ExtensionAPI) {
	const token = process.env.PI_TG_TOKEN, chat = process.env.PI_TG_CHAT;
	if (!token || !chat || process.env.PI_TG_BRIDGE) return;
	let asked = "", answer = "";

	pi.on("agent_end", async (event) => {
		for (const m of event.messages as any[]) {
			if (m.role === "user") asked = textOf(m.content).trim();
			if (m.role === "assistant" && textOf(m.content).trim()) answer = textOf(m.content).trim();
		}
	});

	pi.on("agent_settled", async () => {
		if (!answer) return;
		const msg = `💻 From the terminal\n🙋 ${asked.slice(0, 500)}\n\n${answer}`;
		asked = answer = "";
		for (let i = 0; i < msg.length; i += 4000) {
			try {
				await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
					method: "POST", headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ chat_id: chat, text: msg.slice(i, i + 4000), disable_web_page_preview: true }),
				});
			} catch {}
		}
	});
}
