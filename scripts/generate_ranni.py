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
# CONFIGURAÇÃO DA MOLDURA
# ============================================================

# Espessura da moldura
FRAME_SIZE = 14

# Espaço entre o gráfico e a moldura
FRAME_PADDING = 5

# Tamanho final da imagem
TOTAL_WIDTH = (
    GRAPH_WIDTH
    + (FRAME_SIZE + FRAME_PADDING) * 2
)

TOTAL_HEIGHT = (
    GRAPH_HEIGHT
    + (FRAME_SIZE + FRAME_PADDING) * 2
)

# Onde o gráfico começa dentro da imagem
GRAPH_OFFSET_X = FRAME_SIZE + FRAME_PADDING
GRAPH_OFFSET_Y = FRAME_SIZE + FRAME_PADDING


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
# CARREGAR TEXTURA DO CABO
# ============================================================

sword = Image.open(
    "assets/moonlight.jpg"
).convert("RGBA")


# ============================================================
# RECORTAR SOMENTE O CABO DA ESPADA
# ============================================================

# A textura vem da parte vertical do cabo.
#
# Não usamos a lâmina.
# Não usamos a guarda.
# Apenas a parte trançada do cabo.

handle_texture = sword.crop(
    (
        450,
        1450,
        590,
        1850
    )
)


# ============================================================
# REMOVER FUNDO PRETO DA TEXTURA
# ============================================================

pixels = handle_texture.load()

for y in range(handle_texture.height):

    for x in range(handle_texture.width):

        r, g, b, a = pixels[x, y]

        if r < 35 and g < 35 and b < 35:

            pixels[x, y] = (
                0,
                0,
                0,
                0,
            )


# ============================================================
# CORTAR ESPAÇO TRANSPARENTE
# ============================================================

bbox = handle_texture.getbbox()

if bbox:
    handle_texture = handle_texture.crop(bbox)


# ============================================================
# CRIAR TEXTURA HORIZONTAL
# ============================================================

horizontal_texture = handle_texture.rotate(
    90,
    expand=True
)


# Redimensiona para a espessura da moldura
horizontal_texture = horizontal_texture.resize(
    (
        horizontal_texture.width,
        FRAME_SIZE
    ),
    Image.Resampling.LANCZOS
)


# ============================================================
# CRIAR TEXTURA VERTICAL
# ============================================================

vertical_texture = handle_texture.resize(
    (
        FRAME_SIZE,
        handle_texture.height
    ),
    Image.Resampling.LANCZOS
)


# ============================================================
# FUNÇÃO PARA CRIAR UMA FAIXA DE TEXTURA
# ============================================================

def create_texture_strip(
    texture,
    width,
    height,
    horizontal=True
):

    strip = Image.new(
        "RGBA",
        (
            width,
            height
        ),
        (
            0,
            0,
            0,
            0
        )
    )

    # Tamanho do pedaço que será repetido
    if horizontal:
        tile_width = texture.width
        tile_height = height
    else:
        tile_width = width
        tile_height = texture.height

    position = 0

    while position < (
        width if horizontal else height
    ):

        if horizontal:

            tile = texture

            remaining = width - position

            if tile.width > remaining:

                tile = tile.crop(
                    (
                        0,
                        0,
                        remaining,
                        tile.height
                    )
                )

            strip.alpha_composite(
                tile,
                (
                    position,
                    0
                )
            )

            position += tile_width

        else:

            tile = texture

            remaining = height - position

            if tile.height > remaining:

                tile = tile.crop(
                    (
                        0,
                        0,
                        tile.width,
                        remaining
                    )
                )

            strip.alpha_composite(
                tile,
                (
                    0,
                    position
                )
            )

            position += tile_height

    return strip


# ============================================================
# CRIAR AS QUATRO PARTES DA MOLDURA
# ============================================================

top_frame = create_texture_strip(
    horizontal_texture,
    TOTAL_WIDTH,
    FRAME_SIZE,
    horizontal=True
)

bottom_frame = create_texture_strip(
    horizontal_texture,
    TOTAL_WIDTH,
    FRAME_SIZE,
    horizontal=True
)

left_frame = create_texture_strip(
    vertical_texture,
    FRAME_SIZE,
    TOTAL_HEIGHT,
    horizontal=False
)

right_frame = create_texture_strip(
    vertical_texture,
    FRAME_SIZE,
    TOTAL_HEIGHT,
    horizontal=False
)


# ============================================================
# CRIAR CANTOS DA MOLDURA
# ============================================================

# Os cantos recebem pequenos pedaços da própria textura
# para evitar que fique parecendo quatro linhas separadas.

corner_size = FRAME_SIZE


def create_corner(rotation):

    corner = handle_texture.copy()

    corner.thumbnail(
        (
            corner_size * 2,
            corner_size * 2
        ),
        Image.Resampling.LANCZOS
    )

    corner = corner.rotate(
        rotation,
        expand=True
    )

    corner = corner.resize(
        (
            corner_size,
            corner_size
        ),
        Image.Resampling.LANCZOS
    )

    return corner


corner_tl = create_corner(90)
corner_tr = create_corner(180)
corner_bl = create_corner(0)
corner_br = create_corner(270)


# ============================================================
# DESENHAR MOLDURA
# ============================================================

def draw_frame(image):

    # --------------------------------------------------------
    # GLOW SUAVE
    # --------------------------------------------------------

    frame_layer = Image.new(
        "RGBA",
        image.size,
        (
            0,
            0,
            0,
            0
        )
    )

    frame_layer.alpha_composite(
        top_frame,
        (
            0,
            0
        )
    )

    frame_layer.alpha_composite(
        bottom_frame,
        (
            0,
            TOTAL_HEIGHT - FRAME_SIZE
        )
    )

    frame_layer.alpha_composite(
        left_frame,
        (
            0,
            0
        )
    )

    frame_layer.alpha_composite(
        right_frame,
        (
            TOTAL_WIDTH - FRAME_SIZE,
            0
        )
    )

    # Glow muito discreto
    glow = frame_layer.filter(
        ImageFilter.GaussianBlur(3)
    )

    alpha = glow.getchannel("A")

    alpha = alpha.point(
        lambda value: int(value * 0.22)
    )

    glow.putalpha(alpha)

    image.alpha_composite(
        glow
    )

    # --------------------------------------------------------
    # MOLDURA ORIGINAL
    # --------------------------------------------------------

    image.alpha_composite(
        top_frame,
        (
            0,
            0
        )
    )

    image.alpha_composite(
        bottom_frame,
        (
            0,
            TOTAL_HEIGHT - FRAME_SIZE
        )
    )

    image.alpha_composite(
        left_frame,
        (
            0,
            0
        )
    )

    image.alpha_composite(
        right_frame,
        (
            TOTAL_WIDTH - FRAME_SIZE,
            0
        )
    )

    # --------------------------------------------------------
    # CANTOS
    # --------------------------------------------------------

    image.alpha_composite(
        corner_tl,
        (
            0,
            0
        )
    )

    image.alpha_composite(
        corner_tr,
        (
            TOTAL_WIDTH - FRAME_SIZE,
            0
        )
    )

    image.alpha_composite(
        corner_bl,
        (
            0,
            TOTAL_HEIGHT - FRAME_SIZE
        )
    )

    image.alpha_composite(
        corner_br,
        (
            TOTAL_WIDTH - FRAME_SIZE,
            TOTAL_HEIGHT - FRAME_SIZE
        )
    )

    return image


# ============================================================
# PEGAR CÉLULAS
# ============================================================

cells = []

for x, week in enumerate(weeks):

    for y, day in enumerate(
        week["contributionDays"]
    ):

        px = (
            GRAPH_OFFSET_X
            + x * (CELL_SIZE + GAP)
        )

        py = (
            GRAPH_OFFSET_Y
            + y * (CELL_SIZE + GAP)
        )

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
    GRAPH_OFFSET_X
    + (
        GRAPH_WIDTH
        - ranni.width
    ) // 2
)

ranni_y = (
    GRAPH_OFFSET_Y
    + (
        GRAPH_HEIGHT
        - ranni.height
    ) // 2
)


# ============================================================
# ESCOLHER ALVOS ALEATÓRIOS
# ============================================================

targets = [
    cell
    for cell in cells
    if cell["count"] > 0
]

# Aleatório a cada execução
random.shuffle(targets)

# No máximo 12
# Nunca haverá repetição dentro da mesma animação.
targets = targets[:12]


# ============================================================
# DESENHAR GRÁFICO
# ============================================================

def draw_graph(activated):

    image = Image.new(
        "RGBA",
        (
            TOTAL_WIDTH,
            TOTAL_HEIGHT
        ),
        BACKGROUND
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
        # FOI ATINGIDO
        # ----------------------------------------------------

        elif cell in activated:

            color = activated_blue(
                cell["color"]
            )

        # ----------------------------------------------------
        # CONTRIBUIÇÃO NORMAL
        # ----------------------------------------------------

        else:

            color = cell["color"]

        # ----------------------------------------------------
        # DESENHAR
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

    activated_count = min(
        len(targets),
        frame_number // 10
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
            ranni_y
        )
    )


    # ========================================================
    # ESTRELAS
    # ========================================================

    draw = ImageDraw.Draw(image)

    for i, target in enumerate(targets):

        # ----------------------------------------------------
        # ORIGEM
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
        # DESTINO
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
        # MOVIMENTO
        # ----------------------------------------------------

        progress = (
            frame_number
            - i * 10
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
            # GLOW
            # =================================================

            glow = Image.new(
                "RGBA",
                image.size,
                (
                    0,
                    0,
                    0,
                    0
                )
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
                    100
                )
            )

            glow = glow.filter(
                ImageFilter.GaussianBlur(5)
            )

            image.alpha_composite(
                glow
            )


            # =================================================
            # ESTRELA
            # =================================================

            draw = ImageDraw.Draw(
                image
            )

            draw.line(
                [
                    (x - 4, y),
                    (x + 4, y),
                ],
                fill=STAR_COLOR,
                width=2
            )

            draw.line(
                [
                    (x, y - 4),
                    (x, y + 4),
                ],
                fill=STAR_COLOR,
                width=2
            )


    # ========================================================
    # MOLDURA
    # ========================================================

    image = draw_frame(
        image
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
    exist_ok=True
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
    optimize=False
)

print(
    f"Gráfico gerado: {output}"
)