import os
import random
import requests
from PIL import Image, ImageDraw, ImageFilter

# ============================================================
# GITHUB
# ============================================================

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
# CONFIGURAÇÕES DO GRÁFICO
# ============================================================

CELL_SIZE = 13
GAP = 3

CELL_STEP = CELL_SIZE + GAP

GRAPH_WIDTH = len(weeks) * CELL_STEP
GRAPH_HEIGHT = 7 * CELL_STEP

# Quantidade de frames da animação
FRAMES = 72

# Tempo entre frames
FRAME_DURATION = 70

# Cor quando uma contribuição é atingida pela estrela
BLUE = (70, 180, 255, 255)

# Cor da estrela
STAR = (220, 245, 255, 255)

# Cor do brilho da estrela
GLOW = (80, 190, 255, 130)


# ============================================================
# CARREGAR RANNI - FRAME FIXO
# ============================================================

ranni_source = Image.open("assets/ranni.gif")

# Pega SOMENTE o primeiro frame.
# A Ranni não terá nenhuma animação própria.
ranni_source.seek(0)

ranni = ranni_source.convert("RGBA").copy()

# ------------------------------------------------------------
# RECORTAR A RANNI
# ------------------------------------------------------------

# A imagem original possui bastante espaço preto.
ranni = ranni.crop((320, 490, 490, 811))

# ------------------------------------------------------------
# REMOVER FUNDO PRETO
# ------------------------------------------------------------

pixels = ranni.load()

for y in range(ranni.height):
    for x in range(ranni.width):

        r, g, b, a = pixels[x, y]

        brightness = r + g + b

        if brightness < 80:
            pixels[x, y] = (0, 0, 0, 0)

        elif brightness < 140:
            alpha = int((brightness - 80) / 60 * 255)
            pixels[x, y] = (r, g, b, alpha)

# ------------------------------------------------------------
# RECORTAR NOVAMENTE O ESPAÇO TRANSPARENTE
# ------------------------------------------------------------

bbox = ranni.getbbox()

if bbox:
    ranni = ranni.crop(bbox)

# ------------------------------------------------------------
# TAMANHO
# ------------------------------------------------------------

target_height = 92

ratio = target_height / ranni.height

new_width = int(ranni.width * ratio)

ranni = ranni.resize(
    (new_width, target_height),
    Image.Resampling.LANCZOS,
)


# ============================================================
# PEGAR AS CÉLULAS DO GRÁFICO
# ============================================================

cells = []

for x, week in enumerate(weeks):

    for y, day in enumerate(week["contributionDays"]):

        px = x * CELL_STEP
        py = y * CELL_STEP

        cells.append(
            {
                "x": px,
                "y": py,
                "color": day["color"],
                "count": day["contributionCount"],
            }
        )


# ============================================================
# ESCOLHER DESTINOS DAS ESTRELAS
# ============================================================

# Só usamos quadrados que realmente possuem contribuição.
targets = [
    cell
    for cell in cells
    if cell["count"] > 0
]

random.seed(42)

random.shuffle(targets)

# Número de estrelas
targets = targets[:16]


# ============================================================
# FUNÇÕES
# ============================================================

def center_of(cell):

    return (
        cell["x"] + CELL_SIZE // 2,
        cell["y"] + CELL_SIZE // 2,
    )


def draw_star(image, x, y, size=5):

    # Camada separada para criar o brilho
    glow = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 0),
    )

    glow_draw = ImageDraw.Draw(glow)

    glow_draw.ellipse(
        [
            x - size * 2,
            y - size * 2,
            x + size * 2,
            y + size * 2,
        ],
        fill=GLOW,
    )

    glow = glow.filter(
        ImageFilter.GaussianBlur(6)
    )

    image.alpha_composite(glow)

    draw = ImageDraw.Draw(image)

    # Cruz da estrela
    draw.line(
        [
            (x - size, y),
            (x + size, y),
        ],
        fill=STAR,
        width=2,
    )

    draw.line(
        [
            (x, y - size),
            (x, y + size),
        ],
        fill=STAR,
        width=2,
    )

    # Pontas diagonais menores
    draw.line(
        [
            (x - 2, y - 2),
            (x + 2, y + 2),
        ],
        fill=STAR,
        width=1,
    )

    draw.line(
        [
            (x + 2, y - 2),
            (x - 2, y + 2),
        ],
        fill=STAR,
        width=1,
    )


def draw_graph(activated):

    image = Image.new(
        "RGBA",
        (GRAPH_WIDTH, GRAPH_HEIGHT),
        (255, 255, 255, 255),
    )

    draw = ImageDraw.Draw(image)

    for cell in cells:

        if cell in activated:
            color = BLUE
        else:
            color = cell["color"]

        x = cell["x"]
        y = cell["y"]

        draw.rounded_rectangle(
            [
                x,
                y,
                x + CELL_SIZE,
                y + CELL_SIZE,
            ],
            radius=3,
            fill=color,
        )

    return image


# ============================================================
# ANIMAÇÃO
# ============================================================

frames = []

# Ponto de origem das estrelas:
# centro da Ranni
origin_x = ranni_x + ranni_width // 2
origin_y = ranni_y + ranni_height // 2


for frame_number in range(FRAMES):

    # --------------------------------------------------------
    # CICLO
    # --------------------------------------------------------

    # Depois de um tempo, começamos novamente.
    cycle_frame = frame_number % 48

    activated = []

    # --------------------------------------------------------
    # QUADRADOS JÁ ATINGIDOS
    # --------------------------------------------------------

    for index, target in enumerate(targets):

        hit_frame = 7 + index * 2

        if cycle_frame >= hit_frame:
            activated.append(target)

    image = draw_graph(activated)

    # --------------------------------------------------------
    # ESTRELAS VIAJANDO
    # --------------------------------------------------------

    for index, target in enumerate(targets):

        start_frame = index * 2
        travel_frames = 12

        progress = (
            cycle_frame - start_frame
        ) / travel_frames

        if 0 <= progress <= 1:

            target_x, target_y = center_of(target)

            # Movimento com leve curva
            curve = (
                1 - (2 * progress - 1) ** 2
            )

            x = (
                origin_x
                + (target_x - origin_x) * progress
            )

            y = (
                origin_y
                + (target_y - origin_y) * progress
                - curve * 8
            )

            draw_star(
                image,
                int(x),
                int(y),
                size=5,
            )

    # --------------------------------------------------------
    # RANNI
    # --------------------------------------------------------

    # Ranni fica completamente fixa
    ranni = ranni_frames[0]

    image.alpha_composite(
        ranni,
        (
            ranni_x,
            ranni_y,
        ),
    ),

    frames.append(
        image.convert("P", palette=Image.Palette.ADAPTIVE)
    )


# ============================================================
# SALVAR
# ============================================================

os.makedirs(
    "generated",
    exist_ok=True,
)

output = "generated/ranni-contributions.gif"

frames[0].save(
    output,
    save_all=True,
    append_images=frames[1:],
    duration=FRAME_DURATION,
    loop=0,
    optimize=False,
)

print(
    f"Gráfico gerado com sucesso: {output}"
)