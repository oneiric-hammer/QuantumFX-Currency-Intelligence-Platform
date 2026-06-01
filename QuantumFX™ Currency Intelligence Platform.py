import tkinter as tk
from tkinter import ttk
import requests
import json
import os
from datetime import datetime, timedelta

# ============================================================
#  CONFIG
# ============================================================
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rates_cache.json")
CACHE_MAX_AGE_HOURS = 24  # refresh once per day; set to 0 to force refresh every launch
API_URL = "https://api.frankfurter.app/latest?base=EUR"

# Currencies we want to show (must exist in the API response, EUR is added manually)
SUPPORTED_CURRENCIES = ["EUR", "USD", "GBP", "JPY", "SEK", "CHF", "KRW", "CNY"]

# Emergency fallback rates if there's no internet AND no cache file at all
FALLBACK_RATES = {
    "EUR": 1.0, "USD": 1.16, "GBP": 0.87, "JPY": 184.1,
    "SEK": 10.82, "CHF": 0.91, "KRW": 1736.2, "CNY": 7.98,
}

# ============================================================
#  THEME (one place to recolour the whole app)
# ============================================================
THEME = {
    "bg":        "#1e2229",   # main background
    "card":      "#272c35",   # card panels
    "accent":    "#4a90d9",   # primary blue
    "accent_hi": "#5fa3e8",   # hover blue
    "text":      "#7c899b",   # main text
    "muted":     "#a9abb0",   # secondary text
    "ok":        "#5ec27a",   # green (success / live)
    "warn":      "#e0a93b",   # amber (cached)
    "err":       "#e0604f",   # red (error / offline)
    "field_bg":  "#1a1d23",   # input background
}

# ============================================================
#  TRANSLATIONS
# ============================================================
LANGUAGES = {
    "English": {
        "title": "Currency Converter",
        "amount_label": "Amount",
        "from_label": "From",
        "to_label": "To",
        "convert_btn": "Convert",
        "result_prefix": "",
        "error_empty": "Please enter a valid number.",
        "error_invalid": "Invalid input. Please enter a number.",
        "lang_title": "Select Language",
        "lang_prompt": "Choose your language:",
        "lang_btn": "Continue",
        "refresh_btn": "↻ Refresh rates",
        "swap_tip": "Swap currencies",
        "status_live": "Live rates · updated {time}",
        "status_cached": "Cached rates · from {time}",
        "status_offline": "Offline · using fallback rates",
        "refreshing": "Fetching latest rates…",
    },
    "Deutsch": {
        "title": "Währungsrechner",
        "amount_label": "Betrag",
        "from_label": "Von",
        "to_label": "Nach",
        "convert_btn": "Umrechnen",
        "result_prefix": "",
        "error_empty": "Bitte eine gültige Zahl eingeben.",
        "error_invalid": "Ungültige Eingabe. Bitte eine Zahl eingeben.",
        "lang_title": "Sprache wählen",
        "lang_prompt": "Wähle deine Sprache:",
        "lang_btn": "Weiter",
        "refresh_btn": "↻ Kurse aktualisieren",
        "swap_tip": "Währungen tauschen",
        "status_live": "Live-Kurse · aktualisiert {time}",
        "status_cached": "Gespeicherte Kurse · vom {time}",
        "status_offline": "Offline · Notfallkurse aktiv",
        "refreshing": "Aktuelle Kurse werden geladen…",
    },
    "Svenska": {
        "title": "Valutaomvandlare",
        "amount_label": "Belopp",
        "from_label": "Från",
        "to_label": "Till",
        "convert_btn": "Konvertera",
        "result_prefix": "",
        "error_empty": "Ange ett giltigt nummer.",
        "error_invalid": "Ogiltigt värde. Ange ett nummer.",
        "lang_title": "Välj språk",
        "lang_prompt": "Välj ditt språk:",
        "lang_btn": "Fortsätt",
        "refresh_btn": "↻ Uppdatera kurser",
        "swap_tip": "Byt valutor",
        "status_live": "Live-kurser · uppdaterade {time}",
        "status_cached": "Sparade kurser · från {time}",
        "status_offline": "Offline · reservkurser används",
        "refreshing": "Hämtar senaste kurser…",
    },
    "한국어": {
        "title": "환율 변환기",
        "amount_label": "금액",
        "from_label": "변환 전",
        "to_label": "변환 후",
        "convert_btn": "변환",
        "result_prefix": "",
        "error_empty": "유효한 숫자를 입력해 주세요.",
        "error_invalid": "잘못된 입력입니다. 숫자를 입력해 주세요.",
        "lang_title": "언어 선택",
        "lang_prompt": "언어를 선택하세요:",
        "lang_btn": "계속",
        "refresh_btn": "↻ 환율 새로고침",
        "swap_tip": "통화 교환",
        "status_live": "실시간 환율 · {time} 업데이트",
        "status_cached": "저장된 환율 · {time}",
        "status_offline": "오프라인 · 기본 환율 사용 중",
        "refreshing": "최신 환율을 불러오는 중…",
    },
}


# ============================================================
#  RATE LOADING  (API → cache → fallback)
# ============================================================
def fetch_rates_from_api():
    """Pull fresh rates from the Frankfurter API (ECB data, free, no key)."""
    response = requests.get(API_URL, timeout=8)
    response.raise_for_status()
    data = response.json()
    rates = {code: rate for code, rate in data["rates"].items() if code in SUPPORTED_CURRENCIES}
    rates["EUR"] = 1.0  # base currency isn't included in the response
    return rates


def load_rates(force_refresh=False):
    """
    Returns (rates_dict, status, timestamp).
    status is one of: "live", "cached", "offline".
    Fallback chain: fresh API  ->  cached file  ->  hardcoded fallback.
    """
    # 1. Try the cache first (unless we're forcing a refresh)
    if not force_refresh and os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cache = json.load(f)
            cached_time = datetime.fromisoformat(cache["timestamp"])
            if datetime.now() - cached_time < timedelta(hours=CACHE_MAX_AGE_HOURS):
                return cache["rates"], "cached", cached_time
        except (json.JSONDecodeError, KeyError, ValueError):
            pass  # corrupt cache -> just fetch fresh

    # 2. Cache missing/stale/forced -> hit the API
    try:
        rates = fetch_rates_from_api()
        now = datetime.now()
        with open(CACHE_FILE, "w") as f:
            json.dump({"timestamp": now.isoformat(), "rates": rates}, f, indent=2)
        return rates, "live", now
    except Exception:
        # 3. API failed -> fall back to whatever cache we have, even if stale
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    cache = json.load(f)
                return cache["rates"], "cached", datetime.fromisoformat(cache["timestamp"])
            except (json.JSONDecodeError, KeyError, ValueError):
                pass
        # 4. Nothing at all -> hardcoded emergency rates
        return dict(FALLBACK_RATES), "offline", None


# ============================================================
#  LANGUAGE PICKER
# ============================================================
def pick_language():
    """Show a styled language selection dialog and return the chosen language key."""
    dialog = tk.Tk()
    chosen = tk.StringVar(value="English")
    dialog.title("Language / Sprache / Språk / 언어")
    dialog.configure(bg=THEME["bg"])
    dialog.resizable(False, False)

    wrapper = tk.Frame(dialog, bg=THEME["bg"], padx=40, pady=30)
    wrapper.pack()

    tk.Label(
        wrapper, text="🌐  Choose your language",
        font=("Helvetica", 15, "bold"),
        bg=THEME["bg"], fg=THEME["text"]
    ).pack(pady=(0, 20))

    for lang in LANGUAGES:
        tk.Radiobutton(
            wrapper, text=lang, variable=chosen, value=lang,
            font=("Helvetica", 12), anchor="w",
            bg=THEME["bg"], fg=THEME["text"],
            selectcolor=THEME["field_bg"],
            activebackground=THEME["bg"], activeforeground=THEME["accent_hi"],
            highlightthickness=0, bd=0,
        ).pack(fill="x", padx=20, pady=2)

    btn = tk.Button(
        wrapper, text="Continue  /  Weiter  /  Fortsätt  /  계속",
        command=dialog.destroy,
        font=("Helvetica", 11, "bold"),
        bg=THEME["accent"], fg="white",
        activebackground=THEME["accent_hi"], activeforeground="white",
        relief="flat", padx=14, pady=8, cursor="hand2",
    )
    btn.pack(pady=(24, 0), fill="x")
    btn.bind("<Enter>", lambda e: btn.config(bg=THEME["accent_hi"]))
    btn.bind("<Leave>", lambda e: btn.config(bg=THEME["accent"]))

    dialog.eval("tk::PlaceWindow . center")
    dialog.mainloop()
    return chosen.get()


# ============================================================
#  MAIN CONVERTER WINDOW
# ============================================================
class CurrencyConverter:
    def __init__(self, root, lang_key, rates, status, timestamp):
        self.root = root
        self.t = LANGUAGES[lang_key]
        self.rates = rates

        self.root.title(self.t["title"])
        self.root.configure(bg=THEME["bg"])
        self.root.resizable(False, False)

        # ttk styling for the comboboxes
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Dark.TCombobox",
            fieldbackground=THEME["field_bg"], background=THEME["card"],
            foreground=THEME["text"], arrowcolor=THEME["text"],
            bordercolor=THEME["card"], lightcolor=THEME["card"],
            darkcolor=THEME["card"], selectbackground=THEME["accent"],
            selectforeground="white", padding=6,
        )

        # ---- Header ----
        header = tk.Frame(root, bg=THEME["accent"], height=70)
        header.pack(fill="x")
        tk.Label(
            header, text=self.t["title"],
            font=("Helvetica", 18, "bold"),
            bg=THEME["accent"], fg="white",
        ).pack(pady=18)

        # ---- Body card ----
        body = tk.Frame(root, bg=THEME["bg"], padx=28, pady=22)
        body.pack(fill="both", expand=True)

        # Amount
        self._field_label(body, self.t["amount_label"])
        self.amount_entry = tk.Entry(
            body, font=("Helvetica", 14), justify="center",
            bg=THEME["field_bg"], fg=THEME["text"],
            insertbackground=THEME["text"], relief="flat",
            highlightthickness=1, highlightbackground=THEME["card"],
            highlightcolor=THEME["accent"],
        )
        self.amount_entry.pack(fill="x", ipady=8, pady=(0, 16))
        self.amount_entry.insert(0, "1")

        # From / Swap / To row
        currencies = list(self.rates.keys())

        self._field_label(body, self.t["from_label"])
        self.from_var = tk.StringVar(value="EUR")
        self.from_menu = ttk.Combobox(
            body, textvariable=self.from_var, values=currencies,
            state="readonly", style="Dark.TCombobox", font=("Helvetica", 12),
        )
        self.from_menu.pack(fill="x", pady=(0, 8))

        swap_btn = tk.Button(
            body, text="⇅", command=self.swap_currencies,
            font=("Helvetica", 14, "bold"),
            bg=THEME["card"], fg=THEME["accent_hi"],
            activebackground=THEME["card"], activeforeground=THEME["accent"],
            relief="flat", cursor="hand2", padx=10, pady=2,
        )
        swap_btn.pack(pady=2)

        self._field_label(body, self.t["to_label"])
        self.to_var = tk.StringVar(value="USD" if "USD" in currencies else currencies[0])
        self.to_menu = ttk.Combobox(
            body, textvariable=self.to_var, values=currencies,
            state="readonly", style="Dark.TCombobox", font=("Helvetica", 12),
        )
        self.to_menu.pack(fill="x", pady=(0, 18))

        # Convert button
        self.convert_btn = tk.Button(
            body, text=self.t["convert_btn"], command=self.convert,
            font=("Helvetica", 13, "bold"),
            bg=THEME["accent"], fg="white",
            activebackground=THEME["accent_hi"], activeforeground="white",
            relief="flat", cursor="hand2", pady=10,
        )
        self.convert_btn.pack(fill="x")
        self.convert_btn.bind("<Enter>", lambda e: self.convert_btn.config(bg=THEME["accent_hi"]))
        self.convert_btn.bind("<Leave>", lambda e: self.convert_btn.config(bg=THEME["accent"]))

        # Result
        self.result_label = tk.Label(
            body, text="", font=("Helvetica", 16, "bold"),
            bg=THEME["bg"], fg=THEME["text"], wraplength=300, pady=12,
        )
        self.result_label.pack()

        # ---- Footer / status bar ----
        footer = tk.Frame(root, bg=THEME["card"])
        footer.pack(fill="x", side="bottom")

        self.status_label = tk.Label(
            footer, text="", font=("Helvetica", 9),
            bg=THEME["card"], fg=THEME["muted"], anchor="w", padx=12,
        )
        self.status_label.pack(side="left", pady=6)

        refresh = tk.Button(
            footer, text=self.t["refresh_btn"], command=self.refresh_rates,
            font=("Helvetica", 9), bg=THEME["card"], fg=THEME["muted"],
            activebackground=THEME["card"], activeforeground=THEME["accent_hi"],
            relief="flat", cursor="hand2", padx=12,
        )
        refresh.pack(side="right", pady=6)

        # Bindings & initial state
        self.amount_entry.bind("<Return>", lambda e: self.convert())
        self.set_status(status, timestamp)
        self.convert()

    # ---- helpers ----
    def _field_label(self, parent, text):
        tk.Label(
            parent, text=text, font=("Helvetica", 10, "bold"),
            bg=THEME["bg"], fg=THEME["muted"], anchor="w",
        ).pack(fill="x", pady=(0, 4))

    def set_status(self, status, timestamp):
        time_str = timestamp.strftime("%Y-%m-%d %H:%M") if timestamp else "?"
        if status == "live":
            self.status_label.config(text=self.t["status_live"].format(time=time_str), fg=THEME["ok"])
        elif status == "cached":
            self.status_label.config(text=self.t["status_cached"].format(time=time_str), fg=THEME["warn"])
        else:
            self.status_label.config(text=self.t["status_offline"], fg=THEME["err"])

    def swap_currencies(self):
        a, b = self.from_var.get(), self.to_var.get()
        self.from_var.set(b)
        self.to_var.set(a)
        self.convert()

    def refresh_rates(self):
        self.status_label.config(text=self.t["refreshing"], fg=THEME["muted"])
        self.root.update_idletasks()
        self.rates, status, timestamp = load_rates(force_refresh=True)
        new_currencies = list(self.rates.keys())
        self.from_menu.config(values=new_currencies)
        self.to_menu.config(values=new_currencies)
        self.set_status(status, timestamp)
        self.convert()

    def convert(self):
        raw = self.amount_entry.get().strip()
        if not raw:
            self.result_label.config(text=self.t["error_empty"], fg=THEME["err"])
            return
        try:
            amount = float(raw.replace(",", "."))
        except ValueError:
            self.result_label.config(text=self.t["error_invalid"], fg=THEME["err"])
            return

        from_cur, to_cur = self.from_var.get(), self.to_var.get()
        amount_in_eur = amount / self.rates[from_cur]
        converted = amount_in_eur * self.rates[to_cur]

        self.result_label.config(
            text=f"{amount:,.2f} {from_cur}\n=  {converted:,.2f} {to_cur}",
            fg=THEME["ok"],
        )


# ============================================================
#  ENTRY POINT
# ============================================================
if __name__ == "__main__":
    selected_language = pick_language()

    # Load rates BEFORE building the main window so we can show status immediately
    rates, status, timestamp = load_rates()

    root = tk.Tk()
    app = CurrencyConverter(root, selected_language, rates, status, timestamp)
    root.eval("tk::PlaceWindow . center")
    root.mainloop()
