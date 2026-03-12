"""Internationalization (i18n) service.

Simple key-based translation system. Translations are stored as Python dicts
per language. Templates use {{ t("key") }} for translated strings.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Supported languages
SUPPORTED_LANGUAGES = {
    "en": "English",
    "fr": "Fran\u00e7ais",
    "es": "Espa\u00f1ol",
}

DEFAULT_LANGUAGE = "en"

# Translation dictionaries
# Structure: {lang: {key: translated_string}}
TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # Navigation
        "nav.home": "Home",
        "nav.tools": "Tools",
        "nav.learning_paths": "Learning Paths",
        "nav.progress": "My Progress",
        "nav.readiness": "AI Readiness",
        "nav.strategy": "Strategy",
        "nav.ethics_builder": "Ethics Builder",
        "nav.legal_builder": "Legal Builder",
        "nav.library": "Library",
        "nav.export": "Export Report",
        "nav.benchmarking": "Benchmarking",
        "nav.admin": "Admin",
        "nav.login": "Log In",
        "nav.register": "Register",
        "nav.logout": "Log Out",
        "nav.profile": "Profile",

        # Common
        "common.save": "Save",
        "common.cancel": "Cancel",
        "common.submit": "Submit",
        "common.back": "Back",
        "common.next": "Next",
        "common.loading": "Loading...",
        "common.error": "An error occurred",
        "common.success": "Success",
        "common.no_data": "No data available",
        "common.login_required": "Please log in to access this feature",

        # Progress
        "progress.title": "My Progress",
        "progress.overall": "Overall Completion",
        "progress.ethics_policy": "Ethics Policy",
        "progress.legal_framework": "Legal Framework",
        "progress.strategy_plan": "Strategy Plan",
        "progress.readiness": "AI Readiness",
        "progress.tools_evaluated": "Tools Evaluated",
        "progress.next_step": "Recommended Next Step",

        # Readiness
        "readiness.title": "AI Readiness Assessment",
        "readiness.subtitle": "Discover your organisation's AI maturity level",
        "readiness.start": "Start Assessment",
        "readiness.results": "Your Results",
        "readiness.score": "Overall Score",
        "readiness.maturity": "Maturity Level",

        # Export
        "export.title": "AI Implementation Report",
        "export.subtitle": "Download a comprehensive report of your AI implementation progress",
        "export.preview": "Preview Report",
        "export.download": "Download Report",
        "export.included": "Included",
        "export.create": "Create",

        # Benchmarking
        "benchmarking.title": "Benchmarking",
        "benchmarking.subtitle": "See how your AI adoption compares to peer organisations",
        "benchmarking.your_stage": "Your Adoption Stage",
        "benchmarking.insights": "Insights",
    },

    "fr": {
        # Navigation
        "nav.home": "Accueil",
        "nav.tools": "Outils",
        "nav.learning_paths": "Parcours",
        "nav.progress": "Mon Progr\u00e8s",
        "nav.readiness": "Pr\u00e9paration IA",
        "nav.strategy": "Strat\u00e9gie",
        "nav.ethics_builder": "\u00c9thique IA",
        "nav.legal_builder": "Cadre Juridique",
        "nav.library": "Biblioth\u00e8que",
        "nav.export": "Exporter",
        "nav.benchmarking": "Benchmarking",
        "nav.admin": "Administration",
        "nav.login": "Connexion",
        "nav.register": "S'inscrire",
        "nav.logout": "D\u00e9connexion",
        "nav.profile": "Profil",

        # Common
        "common.save": "Enregistrer",
        "common.cancel": "Annuler",
        "common.submit": "Soumettre",
        "common.back": "Retour",
        "common.next": "Suivant",
        "common.loading": "Chargement...",
        "common.error": "Une erreur est survenue",
        "common.success": "Succ\u00e8s",
        "common.no_data": "Aucune donn\u00e9e disponible",
        "common.login_required": "Veuillez vous connecter pour acc\u00e9der \u00e0 cette fonctionnalit\u00e9",

        # Progress
        "progress.title": "Mon Progr\u00e8s",
        "progress.overall": "Compl\u00e9tion Globale",
        "progress.ethics_policy": "Politique \u00c9thique",
        "progress.legal_framework": "Cadre Juridique",
        "progress.strategy_plan": "Plan Strat\u00e9gique",
        "progress.readiness": "Pr\u00e9paration IA",
        "progress.tools_evaluated": "Outils \u00c9valu\u00e9s",
        "progress.next_step": "Prochaine \u00c9tape Recommand\u00e9e",

        # Readiness
        "readiness.title": "\u00c9valuation de la Pr\u00e9paration IA",
        "readiness.subtitle": "D\u00e9couvrez le niveau de maturit\u00e9 IA de votre organisation",
        "readiness.start": "Commencer l'\u00e9valuation",
        "readiness.results": "Vos R\u00e9sultats",
        "readiness.score": "Score Global",
        "readiness.maturity": "Niveau de Maturit\u00e9",

        # Export
        "export.title": "Rapport de Mise en \u0152uvre IA",
        "export.subtitle": "T\u00e9l\u00e9chargez un rapport complet de votre progression",
        "export.preview": "Aper\u00e7u du Rapport",
        "export.download": "T\u00e9l\u00e9charger",
        "export.included": "Inclus",
        "export.create": "Cr\u00e9er",

        # Benchmarking
        "benchmarking.title": "Benchmarking",
        "benchmarking.subtitle": "Comparez votre adoption de l'IA avec vos pairs",
        "benchmarking.your_stage": "Votre Stade d'Adoption",
        "benchmarking.insights": "Informations",
    },

    "es": {
        # Navigation
        "nav.home": "Inicio",
        "nav.tools": "Herramientas",
        "nav.learning_paths": "Rutas de Aprendizaje",
        "nav.progress": "Mi Progreso",
        "nav.readiness": "Preparaci\u00f3n IA",
        "nav.strategy": "Estrategia",
        "nav.ethics_builder": "\u00c9tica IA",
        "nav.legal_builder": "Marco Legal",
        "nav.library": "Biblioteca",
        "nav.export": "Exportar Informe",
        "nav.benchmarking": "Benchmarking",
        "nav.admin": "Administraci\u00f3n",
        "nav.login": "Iniciar Sesi\u00f3n",
        "nav.register": "Registrarse",
        "nav.logout": "Cerrar Sesi\u00f3n",
        "nav.profile": "Perfil",

        # Common
        "common.save": "Guardar",
        "common.cancel": "Cancelar",
        "common.submit": "Enviar",
        "common.back": "Volver",
        "common.next": "Siguiente",
        "common.loading": "Cargando...",
        "common.error": "Ocurri\u00f3 un error",
        "common.success": "\u00c9xito",
        "common.no_data": "No hay datos disponibles",
        "common.login_required": "Inicie sesi\u00f3n para acceder a esta funci\u00f3n",

        # Progress
        "progress.title": "Mi Progreso",
        "progress.overall": "Completado General",
        "progress.ethics_policy": "Pol\u00edtica \u00c9tica",
        "progress.legal_framework": "Marco Legal",
        "progress.strategy_plan": "Plan Estrat\u00e9gico",
        "progress.readiness": "Preparaci\u00f3n IA",
        "progress.tools_evaluated": "Herramientas Evaluadas",
        "progress.next_step": "Siguiente Paso Recomendado",

        # Readiness
        "readiness.title": "Evaluaci\u00f3n de Preparaci\u00f3n IA",
        "readiness.subtitle": "Descubra el nivel de madurez IA de su organizaci\u00f3n",
        "readiness.start": "Iniciar Evaluaci\u00f3n",
        "readiness.results": "Sus Resultados",
        "readiness.score": "Puntuaci\u00f3n General",
        "readiness.maturity": "Nivel de Madurez",

        # Export
        "export.title": "Informe de Implementaci\u00f3n IA",
        "export.subtitle": "Descargue un informe completo de su progreso",
        "export.preview": "Vista Previa",
        "export.download": "Descargar",
        "export.included": "Incluido",
        "export.create": "Crear",

        # Benchmarking
        "benchmarking.title": "Benchmarking",
        "benchmarking.subtitle": "Vea c\u00f3mo se compara su adopci\u00f3n de IA",
        "benchmarking.your_stage": "Su Etapa de Adopci\u00f3n",
        "benchmarking.insights": "Informaci\u00f3n",
    },
}


def get_locale(request) -> str:
    """Determine the locale for a request.

    Priority:
    1. User preference (if logged in)
    2. Accept-Language header
    3. Default language
    """
    # Check user preference
    user = getattr(request.state, "user", None) if hasattr(request, "state") else None
    if user and hasattr(user, "preferred_language") and user.preferred_language:
        lang = user.preferred_language
        if lang in SUPPORTED_LANGUAGES:
            return lang

    # Check Accept-Language header
    accept = request.headers.get("accept-language", "")
    if accept:
        # Parse simple Accept-Language (e.g., "fr-FR,fr;q=0.9,en;q=0.8")
        for part in accept.split(","):
            lang_tag = part.strip().split(";")[0].strip()
            # Try exact match, then language prefix
            if lang_tag in SUPPORTED_LANGUAGES:
                return lang_tag
            lang_prefix = lang_tag.split("-")[0]
            if lang_prefix in SUPPORTED_LANGUAGES:
                return lang_prefix

    return DEFAULT_LANGUAGE


def translate(key: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """Get a translated string by key.

    Falls back to English if key not found in target language,
    then to the key itself if not found at all.
    """
    # Try target language
    lang_dict = TRANSLATIONS.get(lang, {})
    if key in lang_dict:
        return lang_dict[key]

    # Fallback to English
    if lang != DEFAULT_LANGUAGE:
        en_dict = TRANSLATIONS.get(DEFAULT_LANGUAGE, {})
        if key in en_dict:
            return en_dict[key]

    # Return key as-is
    return key


def t(key: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """Shortcut for translate()."""
    return translate(key, lang)
