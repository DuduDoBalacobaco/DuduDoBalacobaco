import os
import random
import requests

from PIL import Image, ImageDraw, ImageFilter


TOKEN = os.environ["GH_TOKEN"]
USERNAME = os.environ["GITHUB_USERNAME"]

API_URL = "https://api.github.com/graphql"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            contributionCount
            color
          }
        }
      }
    }
  }
}
"""

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

response = requests.post(
    API_URL,
    json={
        "query": QUERY,
        "variables": {"login": USERNAME},
    },
    headers=headers,
)

response.raise_for_status()

data = response.json()

if "errors" in data:
    raise RuntimeError(data["errors"])

weeks = data["data"]["user"]["contributionsCollection"][
    "contributionCalendar"
]["weeks"]


# ============================================================
# CONFIGURAÇÕES
# ============================================================

CELL_SIZE = 12
GAP = 3

GRAPH_WIDTH = len(weeks) * (CELL_SIZE + GAP)
GRAPH_HEIGHT = 7 * (CELL_SIZE + GAP)

# Mais frames + maior duração = animação mais lenta
FRAMES = 120
FRAME_DURATION = 100

# Fundo
BACKGROUND = (24, 28, 34, 255)

# Quadrados normais
GRAY = (75, 82, 92, 255)

# Quadrados atingidos pelas estrelas
BLUE = (80, 180, 255, 255)

STAR_COLOR = (180, 230, 255, 255)


# ============================================================
# CARREGAR RANNI
# ============================================================

ranni = Image.open("assets/ranni.gif").convert("RGBA")

# Recorta apenas a região onde está a Ranni
ranni = ranni.crop((320, 490, 490, 811))

# Redimensiona para caber no gráfico
ranni.thumbnail((100, 100), Image.Resampling.LANCZOS)


# ============================================================
# REMOVER FUNDO PRETO
# ============================================================

pixels = ranni.load()

for y in range(ranni.height):
    for x in range(ranni.width):

        r, g, b, a = pixels[x, y]

        if r < 30 and g < 30 and b < 30:
            pixels[x, y] = (0, 0, 0, 0)


# ============================================================
# PEGAR CÉLULAS
# ============================================================

cells = []

for x, week in enumerate(weeks):

    for y, day in enumerate(week["contributionDays"]):

        px = x * (CELL_SIZE + GAP)
        py = y * (CELL_SIZE + GAP)

        cells.append({
            "x": px,
            "y": py,
            "color": day["color"],
            "count": day["contributionCount"],
        })


# ============================================================
# POSIÇÃO DA RANNI
# ============================================================

ranni_x = (GRAPH_WIDTH - ranni.width) // 2
ranni_y = (GRAPH_HEIGHT - ranni.height) // 2


# ============================================================
# ESCOLHER ALVOS
# ============================================================

random.seed(42)

targets = [
    cell
    for cell in cells
    if cell["count"] > 0
]

random.shuffle(targets)

targets = targets[:12]


# ============================================================
# DESENHAR GRÁFICO
# ============================================================

def draw_graph(activated):

    image = Image.new(
        "RGBA",
        (GRAPH_WIDTH, GRAPH_HEIGHT),
        BACKGROUND,
    )

    draw = ImageDraw.Draw(image)

    for cell in cells:

        # Todos os quadrados começam cinza
        color = GRAY

        # Quadrado atingido pela estrela fica azul
        if cell in activated:
            color = BLUE

        x = cell["x"]
        y = cell["y"]

        draw.rounded_rectangle(
            [
                x,
                y,
                x + CELL_SIZE,
                y + CELL_SIZE,
            ],
            radius=2,
            fill=color,
        )

    return image


# ============================================================
# ANIMAÇÃO
# ============================================================

frames = []

for frame_number in range(FRAMES):

    # Cada estrela ativa um quadrado progressivamente
    activated_count = min(
        len(targets),
        frame_number // 10
    )

    activated = targets[:activated_count]

    image = draw_graph(activated)


    # ========================================================
    # RANNI
    # ========================================================

    image.alpha_composite(
        ranni,
        (ranni_x, ranni_y),
    )


    # ========================================================
    # ESTRELAS
    # ========================================================

    draw = ImageDraw.Draw(image)

    for i, target in enumerate(targets):

        start_x = ranni_x + ranni.width // 2
        start_y = ranni_y + ranni.height // 2

        target_x = target["x"] + CELL_SIZE // 2
        target_y = target["y"] + CELL_SIZE // 2

        # Movimento mais lento
        progress = (frame_number - i * 10) / 20

        if 0 <= progress <= 1:

            x = int(
                start_x +
                (target_x - start_x) * progress
            )

            y = int(
                start_y +
                (target_y - start_y) * progress
            )


            # =================================================
            # BRILHO
            # =================================================

            glow = Image.new(
                "RGBA",
                image.size,
                (0, 0, 0, 0),
            )

            glow_draw = ImageDraw.Draw(glow)

            glow_draw.ellipse(
                [
                    x - 8,
                    y - 8,
                    x + 8,
                    y + 8,
                ],
                fill=(100, 200, 255, 100),
            )

            glow = glow.filter(
                ImageFilter.GaussianBlur(5)
            )

            image.alpha_composite(glow)


            # =================================================
            # ESTRELA
            # =================================================

            draw = ImageDraw.Draw(image)

            draw.line(
                [(x - 4, y), (x + 4, y)],
                fill=STAR_COLOR,
                width=2,
            )

            draw.line(
                [(x, y - 4), (x, y + 4)],
                fill=STAR_COLOR,
                width=2,
            )


    frames.append(image.convert("P"))


# ============================================================
# SALVAR GIF
# ============================================================

os.makedirs("generated", exist_ok=True)

output = "generated/ranni-contributions.gif"

frames[0].save(
    output,
    save_all=True,
    append_images=frames[1:],
    duration=FRAME_DURATION,
    loop=0,
    optimize=False,
)

print(f"Gráfico gerado: {output}")