import tkinter as tk
from tkinter import scrolledtext, ttk
import requests
import threading
import time
import re
import sys
from io import StringIO
import os

# ======================
# CONFIG
# ======================
API_URL = "http://localhost:1234/v1/chat/completions"
MODEL = "local-model"

# ======================
# GLOBAL STATE
# ======================
is_running = False
continuous_mode = False
current_agent_name = ""
current_goal = ""
messages = []
current_step = 0
max_steps = 50   # increased for persistent loop

# ======================
# REAL TOOLS (enhanced for file writing + Ralph-style ReAct loop)
# ======================
def web_search(query: str) -> str:
    try:
        url = f"https://api.duckduckgo.com/?q={requests.utils.quote(query)}&format=json"
        resp = requests.get(url, timeout=12)
        data = resp.json()
        result = ""
        if data.get("Abstract"):
            result += f"📌 {data['Abstract']}\n\n"
        if data.get("RelatedTopics"):
            result += "🔎 Related:\n"
            for t in data["RelatedTopics"][:5]:
                if "Text" in t:
                    result += f"• {t['Text']}\n"
        return result.strip() or "No results."
    except:
        return "⚠️ Web search failed."

def browse_page(url: str) -> str:
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "CatSDK-Agent/1.0"})
        text = resp.text[:8000]
        title = re.search(r'<title>(.*?)</title>', text, re.I)
        title = title.group(1) if title else "Untitled"
        clean = re.sub(r'<[^>]+>', ' ', text)[:800].strip()
        return f"🌐 {title}\n\n{clean}..."
    except:
        return "⚠️ Could not load page."

def code_interpreter(code: str) -> str:
    old_stdout = sys.stdout
    redirected_output = StringIO()
    sys.stdout = redirected_output
    local_namespace = {"__builtins__": {}}
    try:
        exec(code, local_namespace)
        output = redirected_output.getvalue()
        if not output:
            output = "Code executed successfully (no output)."
        return f"✅ Code Output:\n{output}"
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {e}"
    finally:
        sys.stdout = old_stdout

def write_file(path: str, content: str = "") -> str:
    """Real file writing tool - exactly what your goal needs"""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ Successfully wrote blank file to: {path}"
    except Exception as e:
        return f"❌ Failed to write file: {e}"

# ======================
# MAIN WINDOW
# ======================
root = tk.Tk()
root.title("CatSDK 🐱 - Real Autonomous Agent (AgentGPT + Ralph ReAct Loop)")
root.geometry("1380x780")
root.configure(bg="#0f172a")
root.minsize(1100, 700)

# ======================
# HEADER (AgentGPT style)
# ======================
header = tk.Frame(root, bg="#1e2937", height=70)
header.pack(fill="x", side="top")
header.pack_propagate(False)

tk.Label(header, text="🐱", font=("Arial", 28), bg="#1e2937", fg="#34d399").pack(side="left", padx=(20, 8), pady=10)
tk.Label(header, text="CatSDK", font=("Space Grotesk", 26, "bold"), bg="#1e2937", fg="white").pack(side="left", pady=10)
tk.Label(header, text="REAL AGENT", font=("Inter", 10, "bold"), bg="#10b981", fg="#0f172a", padx=12, pady=4).pack(side="left", padx=12, pady=18)

tk.Label(header, text="localhost:1234 • Ralph ReAct Loop + AgentGPT", font=("Inter", 11), bg="#1e2937", fg="#34d399").pack(side="right", padx=20)

# ======================
# LEFT SIDEBAR
# ======================
sidebar = tk.Frame(root, bg="#1e2937", width=260, relief="flat")
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

new_btn = tk.Button(sidebar, text="＋ NEW AGENT", font=("Inter", 14, "bold"), 
                    bg="#111827", fg="#60a5fa", activebackground="#1e2937", activeforeground="#a5f3fc",
                    relief="flat", height=2, command=lambda: show_deploy())
new_btn.pack(padx=20, pady=(30, 20), fill="x")

tk.Label(sidebar, text="YOUR AGENTS", font=("Inter", 10, "bold"), bg="#1e2937", fg="#64748b").pack(anchor="w", padx=28, pady=(10, 5))

agent_list_frame = tk.Frame(sidebar, bg="#1e2937")
agent_list_frame.pack(fill="both", expand=True, padx=15)

demo_agents = ["CatAgent", "ResearchCat", "CodeCat", "MemeCat"]
for name in demo_agents:
    frame = tk.Frame(agent_list_frame, bg="#334155", height=50)
    frame.pack(fill="x", pady=4, padx=4)
    tk.Label(frame, text="🐱", font=("Arial", 18), bg="#334155").pack(side="left", padx=12)
    tk.Label(frame, text=name, font=("Inter", 13), bg="#334155", fg="white").pack(side="left")
    tk.Label(frame, text="✓", font=("Arial", 18), bg="#334155", fg="#34d399").pack(side="right", padx=12)

tk.Frame(sidebar, height=1, bg="#334155").pack(fill="x", padx=20, pady=20)
tk.Label(sidebar, text=f"Model: {MODEL}\nTools: Web • Browse • Code • Write File\nRalph ReAct Loop", 
         font=("Inter", 10), bg="#1e2937", fg="#64748b", justify="left").pack(anchor="w", padx=28)

# ======================
# MAIN AREA
# ======================
main_area = tk.Frame(root, bg="#0f172a")
main_area.pack(side="right", fill="both", expand=True)

# ------------------- DEPLOY PANEL -------------------
deploy_frame = tk.Frame(main_area, bg="#0f172a")

tk.Label(deploy_frame, text="Create a new autonomous agent", font=("Space Grotesk", 32, "bold"), 
         bg="#0f172a", fg="white").pack(anchor="w", padx=60, pady=(60, 8))
tk.Label(deploy_frame, text="Give your cat agent a name and goal.\nIt will run a persistent Ralph ReAct loop (exactly like AgentGPT) until the task is 100% complete.", 
         font=("Inter", 14), bg="#0f172a", fg="#94a3b8", justify="left").pack(anchor="w", padx=60, pady=(0, 40))

tk.Label(deploy_frame, text="AGENT NAME", font=("Inter", 11, "bold"), bg="#0f172a", fg="#64748b").pack(anchor="w", padx=60)
name_entry = tk.Entry(deploy_frame, font=("Inter", 22), bg="#1e2937", fg="white", insertbackground="#34d399",
                      relief="flat", highlightthickness=2, highlightcolor="#34d399")
name_entry.insert(0, "CatAgent")
name_entry.pack(fill="x", padx=60, pady=(8, 30), ipady=12)

tk.Label(deploy_frame, text="YOUR GOAL", font=("Inter", 11, "bold"), bg="#0f172a", fg="#64748b").pack(anchor="w", padx=60)
goal_text = tk.Text(deploy_frame, font=("Inter", 15), bg="#1e2937", fg="white", relief="flat", 
                    highlightthickness=2, highlightcolor="#34d399", height=8, padx=20, pady=20)
goal_text.pack(fill="both", expand=True, padx=60, pady=(8, 40))

deploy_btn = tk.Button(deploy_frame, text="DEPLOY REAL AGENT  🐾", font=("Inter", 18, "bold"), 
                       bg="#111827", fg="#60a5fa", activebackground="#1e2937", activeforeground="#a5f3fc",
                       relief="flat", height=2, command=lambda: deploy_agent())
deploy_btn.pack(fill="x", padx=60, pady=10)

deploy_frame.pack(fill="both", expand=True)

# ------------------- EXECUTION PANEL -------------------
execution_frame = tk.Frame(main_area, bg="#0f172a")

top_bar = tk.Frame(execution_frame, bg="#1e2937", height=70)
top_bar.pack(fill="x")
top_bar.pack_propagate(False)

live_name = tk.Label(top_bar, text="", font=("Inter", 18, "bold"), bg="#1e2937", fg="white")
live_name.pack(side="left", padx=30, pady=20)

status_frame = tk.Frame(top_bar, bg="#10b981", padx=14, pady=6)
status_frame.pack(side="left", pady=20)
tk.Label(status_frame, text="●", font=("Arial", 18), bg="#10b981", fg="#0f172a").pack(side="left")
tk.Label(status_frame, text="RUNNING", font=("Inter", 11, "bold"), bg="#10b981", fg="#0f172a").pack(side="left", padx=4)

continuous_btn = tk.Button(top_bar, text="Continuous Mode OFF", font=("Inter", 12, "bold"), 
                           bg="#111827", fg="#60a5fa", activebackground="#1e2937", activeforeground="#a5f3fc",
                           relief="flat", padx=18, command=lambda: toggle_continuous())
continuous_btn.pack(side="left", padx=10)

run_sh_btn = tk.Button(top_bar, text="RUN.SH", font=("Inter", 12, "bold"), 
                       bg="#111827", fg="#60a5fa", activebackground="#1e2937", activeforeground="#a5f3fc",
                       relief="flat", padx=18, command=lambda: start_run_sh())
run_sh_btn.pack(side="left", padx=10)

stop_btn = tk.Button(top_bar, text="STOP AGENT", font=("Inter", 12, "bold"), 
                     bg="#111827", fg="#ef4444", activebackground="#1e2937", activeforeground="#f87171",
                     relief="flat", padx=20, command=lambda: stop_agent())
stop_btn.pack(side="right", padx=30)

# Log area
log = scrolledtext.ScrolledText(execution_frame, font=("Consolas", 13), bg="#0a1421", fg="#e2e8f0",
                                relief="flat", wrap=tk.WORD, padx=30, pady=30)
log.pack(fill="both", expand=True)

log.tag_config("step", foreground="#64748b", font=("Inter", 11, "bold"))
log.tag_config("thought", foreground="#34d399", font=("Inter", 13))
log.tag_config("action", foreground="#f59e0b", font=("Inter", 13))
log.tag_config("observation", foreground="#a78bfa", font=("Inter", 13))
log.tag_config("code", foreground="#c084fc", font=("Consolas", 13))
log.tag_config("final", foreground="#22c55e", font=("Inter", 13, "bold"))
log.tag_config("plain", foreground="#e2e8f0")

# ======================
# FUNCTIONS
# ======================
def toggle_continuous():
    global continuous_mode
    continuous_mode = not continuous_mode
    continuous_btn.config(text=f"Continuous Mode {'ON' if continuous_mode else 'OFF'}",
                          fg="#22c55e" if continuous_mode else "#60a5fa")

def start_run_sh():
    log.insert(tk.END, "🚀 Running run.sh (AutoGPT 0.4.7 style) — Agent will run continuously...\n", "step")
    log.see(tk.END)
    toggle_continuous()
    if not is_running:
        deploy_agent()

def show_deploy():
    global is_running, continuous_mode
    is_running = False
    continuous_mode = False
    execution_frame.pack_forget()
    deploy_frame.pack(fill="both", expand=True)
    name_entry.delete(0, tk.END)
    name_entry.insert(0, "CatAgent")
    goal_text.delete("1.0", tk.END)

def deploy_agent():
    global current_agent_name, current_goal, messages, current_step, is_running
    current_agent_name = name_entry.get().strip() or "CatAgent"
    current_goal = goal_text.get("1.0", tk.END).strip()
    if not current_goal:
        return
    
    deploy_frame.pack_forget()
    execution_frame.pack(fill="both", expand=True)
    
    log.delete("1.0", tk.END)
    live_name.config(text=f"🐱 {current_agent_name}")
    
    log.insert(tk.END, f"🚀 Real Agent {current_agent_name} deployed!\nGoal: {current_goal}\n\n", "step")
    log.see(tk.END)
    
    messages = [
        {"role": "system", "content": """You are CatSDK, a cozy helpful cat-like autonomous AI agent using Ralph ReAct loop + AgentGPT.
You have real tools. Always respond in this EXACT format (nothing else):

Thought: [your reasoning]
Action: tool_name("parameter")

Available tools: web_search, browse_page, code_interpreter, write_file

When the goal is 100% complete, reply ONLY with:
FINAL ANSWER: [complete final result]"""},
        {"role": "user", "content": f"Goal: {current_goal}\nUse tools and keep going until the task is fully done."}
    ]
    
    current_step = 0
    is_running = True
    threading.Thread(target=agent_loop, daemon=True).start()

def parse_action(reply: str):
    thought = action = final = ""
    for line in reply.split("\n"):
        line = line.strip()
        if line.startswith("Thought:"): thought = line[8:].strip()
        elif line.startswith("Action:"): action = line[7:].strip()
        elif line.startswith("FINAL ANSWER:"): final = line[13:].strip()
    return thought, action, final

def execute_tool(action: str) -> str:
    # write_file (for your exact goal)
    match = re.search(r'write_file\(["\']?([^"\']+)["\']?(?:,\s*["\']?([^"\']*?)["\']?)?\)', action, re.I)
    if match:
        path = match.group(1)
        content = match.group(2) if match.group(2) else ""
        root.after(0, lambda: log.insert(tk.END, f"📁 write_file({path})\n", "action"))
        root.after(0, log.see, tk.END)
        return write_file(path, content)
    
    # web_search
    match = re.search(r'web_search\(["\']?([^"\']+)["\']?\)', action, re.I)
    if match:
        q = match.group(1)
        root.after(0, lambda: log.insert(tk.END, f"🔍 web_search({q})\n", "action"))
        root.after(0, log.see, tk.END)
        return web_search(q)
    
    # browse_page
    match = re.search(r'browse_page\(["\']?([^"\']+)["\']?\)', action, re.I)
    if match:
        u = match.group(1)
        root.after(0, lambda: log.insert(tk.END, f"🌐 browse_page({u})\n", "action"))
        root.after(0, log.see, tk.END)
        return browse_page(u)
    
    # code_interpreter
    match = re.search(r'code_interpreter\(["\']?([\s\S]+?)["\']?\)', action, re.I | re.DOTALL)
    if match:
        code = match.group(1).strip()
        root.after(0, lambda: log.insert(tk.END, f"💻 code_interpreter:\n{code}\n", "code"))
        root.after(0, log.see, tk.END)
        return code_interpreter(code)
    
    return "Unknown tool."

def agent_loop():
    global current_step, is_running, messages
    while is_running and current_step < max_steps:
        current_step += 1
        try:
            # Increased timeout + retry for local model
            for attempt in range(3):
                try:
                    payload = {"model": MODEL, "messages": messages, "temperature": 0.7, "max_tokens": 1200}
                    response = requests.post(API_URL, json=payload, timeout=120)
                    reply = response.json()["choices"][0]["message"]["content"]
                    break
                except requests.exceptions.Timeout:
                    if attempt == 2:
                        raise
                    time.sleep(2)
                    continue
            
            thought, action, final = parse_action(reply)
            
            root.after(0, lambda t=thought, a=action, f=final, s=current_step: update_log(t, a, f, s))
            
            if final:
                root.after(0, lambda: log.insert(tk.END, f"\n🎉 FINAL ANSWER: {final}\n", "final"))
                is_running = False
                break
            
            # Ralph ReAct Loop - always continue until final
            if action:
                observation = execute_tool(action)
                messages.append({"role": "assistant", "content": reply})
                messages.append({"role": "user", "content": f"Observation: {observation}\nContinue working toward the goal."})
            else:
                messages.append({"role": "assistant", "content": reply})
                messages.append({"role": "user", "content": "Continue working toward the goal."})
            
            time.sleep(0.8)
            
        except Exception as e:
            root.after(0, lambda e=e: log.insert(tk.END, f"\n❌ Error: {e}\n", "plain"))
            time.sleep(3)  # wait and retry
            continue

def update_log(thought, action, final, step):
    log.insert(tk.END, f"STEP {step} — ", "step")
    if thought:
        log.insert(tk.END, f"Thought: {thought}\n", "thought")
    if action:
        log.insert(tk.END, f"Action: {action}\n", "action")
    if final:
        log.insert(tk.END, f"\nFINAL ANSWER: {final}\n\n", "final")
    else:
        log.insert(tk.END, "\n", "plain")
    log.see(tk.END)

def stop_agent():
    global is_running
    is_running = False
    root.after(0, lambda: log.insert(tk.END, "\n🛑 Agent stopped by user.\n", "plain"))
    log.see(tk.END)

# ======================
# RUN
# ======================
root.mainloop()
