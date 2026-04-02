#!/bin/bash
# ============================================================
# Setup script — Balance de Masas App
# Ejecutar desde el Mac Mini: bash setup.sh
# ============================================================

set -e

echo "================================================"
echo "  Balance de Masas Cu/H₂SO₄ — Setup Inicial"
echo "================================================"
echo ""

# 1. Verificar Python
echo "→ Verificando Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "  ✓ $PYTHON_VERSION"
else
    echo "  ✗ Python3 no encontrado. Instálalo con:"
    echo "    brew install python@3.11"
    exit 1
fi

# 2. Crear entorno virtual
echo ""
echo "→ Creando entorno virtual..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  ✓ Entorno virtual creado"
else
    echo "  ✓ Entorno virtual ya existe"
fi

# 3. Activar e instalar dependencias
echo ""
echo "→ Instalando dependencias..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  ✓ Dependencias instaladas"

# 4. Verificar estructura
echo ""
echo "→ Verificando estructura del proyecto..."
DIRS=("modules" "modules/heap_franja" "tests" "data/synthetic" "templates" "assets" "docs")
for dir in "${DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo "  + Creado $dir/"
    fi
done

# Init files
for init in modules/__init__.py modules/heap_franja/__init__.py tests/__init__.py; do
    if [ ! -f "$init" ]; then
        touch "$init"
    fi
done
echo "  ✓ Estructura OK"

# 5. Verificar Claude Code
echo ""
echo "→ Verificando Claude Code..."
if command -v claude &> /dev/null; then
    CLAUDE_VERSION=$(claude --version 2>/dev/null || echo "instalado")
    echo "  ✓ Claude Code: $CLAUDE_VERSION"
else
    echo "  ✗ Claude Code no encontrado. Instálalo con:"
    echo "    curl -fsSL https://claude.ai/install.sh | bash"
    echo ""
    echo "  Luego autentícate corriendo: claude"
    echo "  (Se abrirá el navegador para login)"
fi

# 6. Inicializar git
echo ""
echo "→ Configurando Git..."
if [ ! -d ".git" ]; then
    git init -q
    echo "  ✓ Repositorio Git inicializado"
else
    echo "  ✓ Repositorio Git ya existe"
fi

# Crear .gitignore
if [ ! -f ".gitignore" ]; then
cat > .gitignore << 'EOF'
venv/
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
build/
credentials/
*.json
!templates/*.json
.env
.DS_Store
data/synthetic/*.csv
EOF
    echo "  ✓ .gitignore creado"
fi

echo ""
echo "================================================"
echo "  ✓ Setup completo!"
echo "================================================"
echo ""
echo "Próximos pasos:"
echo ""
echo "  1. Activar entorno virtual:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Iniciar Claude Code:"
echo "     claude"
echo ""
echo "  3. Pedirle que implemente la Iteración 1:"
echo "     → 'Lee CLAUDE.md y los docs en docs/."
echo "        Implementa la Iteración 1 completa:"
echo "        models.py, config.py, weighted_input.py,"
echo "        copper_balance.py, acid_balance.py,"
echo "        leach_ratio.py, holdup.py, gangue_proxies.py."
echo "        Genera datos sintéticos realistas y tests"
echo "        para un pad con 3 franjas y 2-3 módulos"
echo "        cada una, 90 días de operación.'"
echo ""
echo "  4. Correr la app (cuando el dashboard esté listo):"
echo "     python app.py"
echo "     → Abrir http://localhost:8050"
echo ""
