import os
import random
import requests

from PIL import Image, ImageDraw, ImageFilter


# ============================================================
# GITHUB API
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
        "variables": {
            "login": USERNAME
        },
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

# Animação
FRAMES = 120
FRAME_DURATION = 100

# Fundo
BACKGROUND = (24, 28, 34, 255)

# Quadrados sem contribuição
GRAY = (75, 82, 92, 255)

# Cor das estrelas
STAR_COLOR = (180, 230, 255, 255)


# ============================================================
# CONVERTER VERDE → AZUL
# ============================================================

def green_to_blue(color):
    """
    Converte a cor verde original do GitHub
    para uma tonalidade azul equivalente.
    """

    color = color.lstrip("#")

    r = int(color[0:2], 16)
    g = int(color[2:4], 16)
    b = int(color[4:6], 16)

    intensity = g / 255

    blue = int(110 + intensity * 145)
    green = int(90 + intensity * 100)
    red = int(30 + intensity * 40)

    return (
        red,
        green,
        blue,
        255,
    )


# ============================================================
# AZUL MAIS BRILHANTE QUANDO A ESTRELA ATINGE
# ============================================================

def activated_blue(color):

    base = green_to_blue(color)

    r, g, b, a = base

    return (
        min(255, r + 25),
        min(255, g + 35),
        min(255, b + 25),
        255,
    )


# ============================================================
# CARREGAR RANNI
# ============================================================

ranni = Image.open(
    "assets/ranni.gif"
).convert("RGBA")


# Recorta apenas a Ranni
ranni = ranni.crop(
    (320, 490, 490, 811)
)


# Redimensiona
ranni.thumbnail(
    (100, 100),
    Image.Resampling.LANCZOS
)


# ============================================================
# REMOVER FUNDO PRETO DA RANNI
# ============================================================

pixels = ranni.load()

for y in range(ranni.height):

    for x in range(ranni.width):

        r, g, b, a = pixels[x, y]

        if r < 30 and g < 30 and b < 30:

            pixels[x, y] = (
                0,
                0,
                0,
                0,
            )


# ============================================================
# CARREGAR ESPADA
# ============================================================

sword = Image.open(
    "assets/moonlight.jpg"
).convert("RGBA")


# ============================================================
# REMOVER FUNDO PRETO DA ESPADA
# ============================================================

pixels = sword.load()

for y in range(sword.height):

    for x in range(sword.width):

        r, g, b, a = pixels[x, y]

        # Detecta o fundo preto
        if r < 30 and g < 30 and b < 30:

            pixels[x, y] = (
                0,
                0,
                0,
                0,
            )


# ============================================================
# CORTAR ESPAÇOS VAZIOS DA ESPADA
# ============================================================

bbox = sword.getbbox()

if bbox:
    sword = sword.crop(bbox)


# ============================================================
# GIRAR ESPADA PARA HORIZONTAL
# ============================================================

sword = sword.rotate(
    90,
    expand=True
)


# ============================================================
# REDIMENSIONAR ESPADA
# ============================================================

# Mantém uma margem nas laterais
SWORD_WIDTH = GRAPH_WIDTH - 30

sword.thumbnail(
    (SWORD_WIDTH, 150),
    Image.Resampling.LANCZOS
)


# ============================================================
# ESPAÇO RESERVADO PARA A ESPADA
# ============================================================

SWORD_MARGIN_TOP = 8
SWORD_MARGIN_BOTTOM = 8

SWORD_SPACE = (
    sword.height
    + SWORD_MARGIN_TOP
    + SWORD_MARGIN_BOTTOM
)

TOTAL_HEIGHT = (
    GRAPH_HEIGHT
    + SWORD_SPACE
)


# ============================================================
# PEGAR CÉLULAS
# ============================================================

cells = []

for x, week in enumerate(weeks):

    for y, day in enumerate(
        week["contributionDays"]
    ):

        px = x * (CELL_SIZE + GAP)
        py = y * (CELL_SIZE + GAP)

        cells.append(
            {
                "x": px,
                "y": py,
                "color": day["color"],
                "count": day["contributionCount"],
            }
        )


# ============================================================
# POSIÇÃO DA RANNI
# ============================================================

ranni_x = (
    GRAPH_WIDTH - ranni.width
) // 2

ranni_y = (
    GRAPH_HEIGHT - ranni.height
) // 2


# ============================================================
# ESCOLHER ALVOS ALEATÓRIOS
# ============================================================

# Somente quadrados que possuem contribuição
targets = [
    cell
    for cell in cells
    if cell["count"] > 0
]


# Embaralha completamente
random.shuffle(targets)


# Pega no máximo 12
# Como a lista foi embaralhada e cada célula
# existe apenas uma vez, não haverá repetição.
targets = targets[:12]


# ============================================================
# DESENHAR GRÁFICO
# ============================================================

def draw_graph(activated):

    image = Image.new(
        "RGBA",
        (
            GRAPH_WIDTH,
            TOTAL_HEIGHT,
        ),
        BACKGROUND,
    )

    draw = ImageDraw.Draw(image)


    # ========================================================
    # QUADRADOS
    # ========================================================

    for cell in cells:

        # ----------------------------------------------------
        # SEM CONTRIBUIÇÃO
        # ----------------------------------------------------

        if cell["count"] == 0:

            color = GRAY


        # ----------------------------------------------------
        # FOI ATINGIDO PELA ESTRELA
        # ----------------------------------------------------

        elif cell in activated:

            color = activated_blue(
                cell["color"]
            )


        # ----------------------------------------------------
        # CONTRIBUIÇÃO NORMAL
        # MANTÉM O VERDE ORIGINAL
        # ----------------------------------------------------

        else:

            color = cell["color"]


        # ----------------------------------------------------
        # DESENHAR QUADRADO
        # ----------------------------------------------------

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


    # ========================================================
    # QUADRADOS ATIVADOS
    # ========================================================

    # A cada 10 frames uma estrela chega
    activated_count = min(
        len(targets),
        frame_number // 10,
    )

    activated = targets[
        :activated_count
    ]


    # ========================================================
    # GRÁFICO
    # ========================================================

    image = draw_graph(
        activated
    )


    # ========================================================
    # RANNI
    # ========================================================

    image.alpha_composite(
        ranni,
        (
            ranni_x,
            ranni_y,
        ),
    )


    # ========================================================
    # ESTRELAS
    # ========================================================

    draw = ImageDraw.Draw(image)


    for i, target in enumerate(targets):


        # ----------------------------------------------------
        # ORIGEM = CENTRO DA RANNI
        # ----------------------------------------------------

        start_x = (
            ranni_x
            + ranni.width // 2
        )

        start_y = (
            ranni_y
            + ranni.height // 2
        )


        # ----------------------------------------------------
        # DESTINO = CENTRO DO QUADRADO
        # ----------------------------------------------------

        target_x = (
            target["x"]
            + CELL_SIZE // 2
        )

        target_y = (
            target["y"]
            + CELL_SIZE // 2
        )


        # ----------------------------------------------------
        # MOVIMENTO DA ESTRELA
        # ----------------------------------------------------

        progress = (
            frame_number - i * 10
        ) / 20


        if 0 <= progress <= 1:


            x = int(
                start_x
                + (
                    target_x
                    - start_x
                ) * progress
            )

            y = int(
                start_y
                + (
                    target_y
                    - start_y
                ) * progress
            )


            # =================================================
            # GLOW DA ESTRELA
            # =================================================

            glow = Image.new(
                "RGBA",
                image.size,
                (
                    0,
                    0,
                    0,
                    0,
                ),
            )


            glow_draw = ImageDraw.Draw(
                glow
            )


            glow_draw.ellipse(
                [
                    x - 8,
                    y - 8,
                    x + 8,
                    y + 8,
                ],
                fill=(
                    100,
                    200,
                    255,
                    100,
                ),
            )


            glow = glow.filter(
                ImageFilter.GaussianBlur(
                    5
                )
            )


            image.alpha_composite(
                glow
            )


            # =================================================
            # ESTRELA
            # =================================================

            draw = ImageDraw.Draw(image)


            draw.line(
                [
                    (x - 4, y),
                    (x + 4, y),
                ],
                fill=STAR_COLOR,
                width=2,
            )


            draw.line(
                [
                    (x, y - 4),
                    (x, y + 4),
                ],
                fill=STAR_COLOR,
                width=2,
            )


    # ========================================================
    # ESPADA / MOLDURA
    # ========================================================

    sword_x = (
        GRAPH_WIDTH - sword.width
    ) // 2

    sword_y = (
        GRAPH_HEIGHT
        + SWORD_MARGIN_TOP
    )


    # ========================================================
    # GLOW DA ESPADA
    # ========================================================

    sword_glow = Image.new(
        "RGBA",
        image.size,
        (
            0,
            0,
            0,
            0,
        ),
    )


    sword_glow_x = sword_x
    sword_glow_y = sword_y


    sword_glow.alpha_composite(
        sword,
        (
            sword_glow_x,
            sword_glow_y,
        ),
    )


    sword_glow = sword_glow.filter(
        ImageFilter.GaussianBlur(4)
    )


    # Deixa o glow mais discreto
    alpha = sword_glow.getchannel("A")

    alpha = alpha.point(
        lambda value: int(value * 0.25)
    )

    sword_glow.putalpha(alpha)


    image.alpha_composite(
        sword_glow
    )


    # ========================================================
    # ESPADA ORIGINAL
    # ========================================================

    image.alpha_composite(
        sword,
        (
            sword_x,
            sword_y,
        ),
    )


    # ========================================================
    # SALVAR FRAME
    # ========================================================

    frames.append(
        image.convert("P")
    )


# ============================================================
# SALVAR GIF
# ============================================================

os.makedirs(
    "generated",
    exist_ok=True,
)


output = (
    "generated/"
    "ranni-contributions.gif"
)


frames[0].save(
    output,
    save_all=True,
    append_images=frames[1:],
    duration=FRAME_DURATION,
    loop=0,
    optimize=False,
)


print(
    f"Gráfico gerado: {output}"
)