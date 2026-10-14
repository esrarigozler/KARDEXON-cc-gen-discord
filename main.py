import random
import math
import discord
from discord.ext import commands
from datetime import datetime, timedelta

BOT_TOKEN = "KENDİ TOKENİNİZİ YAZIN"
OWNER_ID = 123456789012345678  



def format_card_number(number: str, card_type: str) -> str:
    if card_type == "American Express":
        if len(number) == 15:
            return f"{number[:4]} {number[4:10]} {number[10:]}"
        return number
    else:
        if len(number) == 16:
            return " ".join(number[i:i+4] for i in range(0, 16, 4))
        return number

def mask_card(number: str) -> str:
    return "**** **** **** " + number[-4:]

def entropy(number: str) -> float:
    counts = {}
    for d in number:
        counts[d] = counts.get(d, 0) + 1
    length = len(number)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())

def has_repeated_blocks(number: str) -> bool:
    return any(d * 4 in number for d in "0123456789")

def has_sequence(number: str) -> bool:
    for i in range(len(number) - 3):
        seq = number[i:i+4]
        if seq in ("0123","1234","2345","3456","4567","5678","6789","7890",
                   "9876","8765","7654","6543","5432","4321","3210"):
            return True
    return False

def quality_score(number: str, luhn_ok: bool, card_type: str) -> int:
    score = 0
    if luhn_ok:
        score += 40
    if card_type != "Unknown":
        score += 25
    if not has_repeated_blocks(number):
        score += 15
    if not has_sequence(number):
        score += 10
    if entropy(number) > 3.5:
        score += 10
    return score

def luhn_check(number: str) -> bool:
    digits = [int(d) for d in number]
    checksum = 0
    for i, d in enumerate(digits[::-1]):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0

def calculate_check_digit(partial: str) -> str:
    for d in range(10):
        if luhn_check(partial + str(d)):
            return str(d)
    return "0"

class AdvancedCC:
    def __init__(self):
        self.config = {
            "Visa": {
                "length": 16, "cvv": 3,
                "bin_valid": lambda p: p.startswith("4")
            },
            "Mastercard": {
                "length": 16, "cvv": 3,
                "bin_valid": self._is_mastercard_bin
            },
            "American Express": {
                "length": 15, "cvv": 4,
                "bin_valid": lambda p: p.startswith("34") or p.startswith("37")
            },
            "Discover": {
                "length": 16, "cvv": 3,
                "bin_valid": self._is_discover_bin
            },
            "JCB": {
                "length": 16, "cvv": 3,
                "bin_valid": self._is_jcb_bin
            }
        }

    def _is_mastercard_bin(self, p: str) -> bool:
        if not p.isdigit(): return False
        if len(p) >= 2 and 51 <= int(p[:2]) <= 55:
            return True
        if len(p) >= 6 and 222100 <= int(p[:6]) <= 272099:
            return True
        if len(p) >= 4 and 2221 <= int(p[:4]) <= 2720:
            return True
        return False

    def _is_discover_bin(self, p: str) -> bool:
        if not p.isdigit(): return False
        if p.startswith("6011") or p.startswith("65"):
            return True
        if len(p) >= 3 and 644 <= int(p[:3]) <= 649:
            return True
        if len(p) >= 6 and 622126 <= int(p[:6]) <= 622925:
            return True
        return False

    def _is_jcb_bin(self, p: str) -> bool:
        if not p.isdigit(): return False
        if len(p) >= 4 and 3528 <= int(p[:4]) <= 3589:
            return True
        if len(p) >= 2 and p[:2] == "35":
            return True
        return False

    def identify_card_type(self, number: str) -> str:
        for name, cfg in self.config.items():
            if len(number) == cfg["length"] and cfg["bin_valid"](number):
                return name
        return "Unknown"

    def generate_cvv(self, card_type: str) -> str:
        length = self.config.get(card_type, {}).get("cvv", 3)
        return f"{random.randint(0, 10**length - 1):0{length}d}"

    def generate_expiry(self) -> str:
        future = datetime.now() + timedelta(days=random.randint(365, 365*5))
        return future.strftime("%m/%Y")

    def generate_luhn_card(self, card_type: str, prefix: str = None) -> str:
        cfg = self.config[card_type]
        if prefix is not None:
            if not prefix.isdigit():
                raise ValueError("BIN sadece rakamlardan oluşmalı.")
            if len(prefix) > cfg["length"] - 1:
                raise ValueError(f"BIN en fazla {cfg['length']-1} haneli olabilir.")
            if not cfg["bin_valid"](prefix):
                raise ValueError(f"BIN ({prefix}) {card_type} için geçerli değil.")
            selected = prefix
        else:
            if card_type == "Visa":
                selected = "4"
            elif card_type == "American Express":
                selected = random.choice(["34", "37"])
            else:
                if card_type == "Mastercard":
                    if random.random() < 0.5:
                        selected = str(random.randint(51, 55))
                    else:
                        selected = str(random.randint(222100, 272099))
                elif card_type == "Discover":
                    r = random.random()
                    if r < 0.3: selected = "6011"
                    elif r < 0.6: selected = "65"
                    else: selected = str(random.randint(622126, 622925))
                elif card_type == "JCB":
                    selected = str(random.randint(3528, 3589))
                else:
                    selected = "4"
        remaining = cfg["length"] - len(selected) - 1
        if remaining < 0:
            raise ValueError("BIN çok uzun.")
        body = selected + str(random.randint(0, 10**remaining - 1)).zfill(remaining)
        return body + calculate_check_digit(body)

    def generate_filtered_cards(self, card_type: str, count: int,
                                bin_prefix: str = None, min_score: int = None,
                                no_sequence: bool = False, no_repeat: bool = False,
                                include_extra: bool = True, max_attempts: int = 3000):
        cards = []
        attempts = 0
        while len(cards) < count and attempts < max_attempts:
            attempts += 1
            try:
                number = self.generate_luhn_card(card_type, bin_prefix)
            except ValueError:
                continue
            ctype = self.identify_card_type(number)
            if ctype == "Unknown":
                continue
            if no_sequence and has_sequence(number):
                continue
            if no_repeat and has_repeated_blocks(number):
                continue
            score = quality_score(number, True, ctype)
            if min_score is not None and score < min_score:
                continue
            card = {
                "card_type": ctype,
                "number_raw": number,
                "number": format_card_number(number, ctype),
                "score": score
            }
            if include_extra:
                card["cvv"] = self.generate_cvv(ctype)
                card["expiry"] = self.generate_expiry()
            cards.append(card)
        return cards[:count]


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

TYPE_MAP = {
    "visa": "Visa",
    "mc": "Mastercard",
    "mastercard": "Mastercard",
    "amex": "American Express",
    "americanexpress": "American Express",
    "discover": "Discover",
    "jcb": "JCB"
}

@bot.event
async def on_ready():
    print(f"✅ {bot.user} olarak giriş yapıldı!")

@bot.command(name="komutlar")
async def yardim(ctx):
    embed = discord.Embed(title="📋 Komut Menüsü", color=0x3498db)
    embed.add_field(
        name="!kart <tip> [adet] [opsiyonlar]",
        value=(
            "**Açıklama:** Belirtilen türde kredi kartı numarası üretir.\n"
            "**Parametreler:**\n"
            "• `<tip>` → Kart markası (zorunlu)\n"
            "• `[adet]` → 1‑100 (varsayılan 5)\n"
            "• `[--bin BIN]` → Başlangıç BIN numarası\n"
            "• `[--min-score X]` → Skor ≥ X olanları göster (0‑100)\n"
            "• `[--no-sequence]` → Ardışık rakam dizilerini ele\n"
            "• `[--no-repeat]` → Tekrarlayan blokları (0000) ele\n"
            "**Tipler:** `visa`, `mc`, `amex`, `discover`, `jcb`\n"
            "**Örnek:** `!kart visa 10 --bin 4612 --no-repeat`"
        ),
        inline=False
    )
    embed.add_field(name="!komutlar", value="Yardım menüsünü gösterir.", inline=False)
    embed.set_footer(text="Bot esrarigozler tarafından yapılmıştır.")
    await ctx.send(embed=embed)

@bot.command(name="kart")
async def kart_uret(ctx, tip: str = None, adet: int = 5, *, flags: str = ""):
    if tip is None:
        await ctx.send("🚫 Kart tipi belirtin: `!kart visa 5`")
        return

    card_class = TYPE_MAP.get(tip.lower())
    if not card_class:
        await ctx.send("❌ Geçersiz tip. visa, mc, amex, discover, jcb")
        return

    if adet < 1 or adet > 100:
        await ctx.send("⚠️ Adet 1-100 arasında olmalı.")
        return
    bin_prefix = None
    min_score = None
    no_sequence = False
    no_repeat = False
    if flags:
        parts = flags.split()
        i = 0
        while i < len(parts):
            p = parts[i]
            if p == "--bin" and i+1 < len(parts):
                bin_prefix = parts[i+1]
                i += 2
            elif p == "--min-score" and i+1 < len(parts):
                try:
                    min_score = int(parts[i+1])
                    if not 0 <= min_score <= 100:
                        raise ValueError
                except ValueError:
                    await ctx.send("❌ --min-score 0-100 arası sayı olmalı.")
                    return
                i += 2
            elif p == "--no-sequence":
                no_sequence = True
                i += 1
            elif p == "--no-repeat":
                no_repeat = True
                i += 1
            else:
                i += 1

    cc = AdvancedCC()
    try:
        cards = cc.generate_filtered_cards(
            card_type=card_class,
            count=adet,
            bin_prefix=bin_prefix,
            min_score=min_score,
            no_sequence=no_sequence,
            no_repeat=no_repeat,
            include_extra=True,
            max_attempts=3000
        )
    except ValueError as e:
        await ctx.send(f"❌ Hata: {e}")
        return

    if not cards:
        await ctx.send("⚠️ Filtrelere uygun kart bulunamadı.")
        return
    card_list = []
    for c in cards:
        ay = c["expiry"][:2]
        yil = c["expiry"][3:]
        line = f"{c['number_raw']}|{ay}|{yil}|{c['cvv']}"
        card_list.append(line)

    filter_desc = []
    if bin_prefix: filter_desc.append(f"BIN: {bin_prefix}")
    if min_score is not None: filter_desc.append(f"Min Skor: {min_score}")
    if no_sequence: filter_desc.append("Ardışık sayı yok")
    if no_repeat: filter_desc.append("Tekrar blok yok")
    filter_text = ", ".join(filter_desc) if filter_desc else "Yok"

    embed = discord.Embed(
        title="Üretilen Kartlar",
        description=f"**Tip:** {card_class}\n**Adet:** {len(card_list)}\n**Filtreler:** {filter_text}",
        color=0x00ff00
    )
    for i in range(0, len(card_list), 10):
        chunk = card_list[i:i+10]
        name = "Kart Listesi" if i == 0 else "\u200b"
        embed.add_field(name=name, value=f"```{chr(10).join(chunk)}```", inline=False)

    embed.set_footer(text="Bot esrarigozler tarafından yapılmıştır.")
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Eksik parametre. Kullanım: `!kart <tip> [adet]`")
    else:
        print(f"Hata: {error}")
        await ctx.send("⚠️ Bir hata oluştu, lütfen tekrar deneyin.")

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
