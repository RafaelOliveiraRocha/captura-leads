"""Entrada explícita da coleta externa; importar este módulo não inicia a coleta."""

from externo import main


if __name__ == "__main__":
    main(timeout_padrao=35, pausa_padrao=10)
