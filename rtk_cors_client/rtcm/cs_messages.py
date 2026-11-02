# -*- coding: utf-8 -*-
"""Словарь описаний сообщений системы координат (RTCM 1021-1027, 1300, 1302).

Вынесено из монолитного rtk4.py без изменений для обеспечения обратной совместимости.
"""

# ============================================================================
# ⭐ НОВОЕ: СООБЩЕНИЯ СИСТЕМЫ КООРДИНАТ (1021-1027, 1300, 1302)
# ============================================================================

COORDINATE_SYSTEM_MESSAGES = {
    1021: {
        "name": "Helmert / Molodensky (упрощенное)",
        "description": "7 параметров преобразования Гельмерта + параметры эллипсоидов",
        "fields": {
            "DF386": "Message Number",
            "DF387": "Reference-Station ID",
            "DF390": "Source-System ID",
            "DF391": "Target-System ID",
            "DF403": "Transformation Method (0=Helmert, 1=Molodensky)",
            "DF392": "Sigma translation X (mm)",
            "DF393": "Sigma translation Y (mm)",
            "DF394": "Sigma translation Z (mm)",
            "DF388": "Translation X (mm)",
            "DF389": "Translation Y (mm)",
            "DF405": "Translation Z (mm)",
            "DF395": "Sigma rotation X (0.0001 arcsec)",
            "DF396": "Sigma rotation Y (0.0001 arcsec)",
            "DF397": "Sigma rotation Z (0.0001 arcsec)",
            "DF398": "Rotation X (0.0001 arcsec)",
            "DF399": "Rotation Y (0.0001 arcsec)",
            "DF406": "Rotation Z (0.0001 arcsec)",
            "DF400": "Sigma scale (1e-8)",
            "DF401": "Scale (1e-8)",
            "DF407": "Source ellipsoid (DA, DF)",
            "DF402": "Target ellipsoid (DA, DF)",
            "DF404": "Horizontal shift residuals",
            "DF408": "Vertical shift residuals",
            "DF409": "Iteration limit",
            "DF410": "Number of residuals",
        }
    },
    1022: {
        "name": "Molodensky-Badekas",
        "description": "10 параметров преобразования + координаты центра вращения",
        "fields": {
            "DF386": "Message Number",
            "DF387": "Reference-Station ID",
            "DF390": "Source-System ID",
            "DF391": "Target-System ID",
            "DF403": "Transformation Method",
            "DF392": "Sigma translation X",
            "DF393": "Sigma translation Y",
            "DF394": "Sigma translation Z",
            "DF388": "Translation X",
            "DF389": "Translation Y",
            "DF405": "Translation Z",
            "DF395": "Sigma rotation X",
            "DF396": "Sigma rotation Y",
            "DF397": "Sigma rotation Z",
            "DF398": "Rotation X",
            "DF399": "Rotation Y",
            "DF406": "Rotation Z",
            "DF400": "Sigma scale",
            "DF401": "Scale",
            "DF407": "Source ellipsoid",
            "DF402": "Target ellipsoid",
            "DF411": "X rotation point (m)",
            "DF412": "Y rotation point (m)",
            "DF413": "Z rotation point (m)",
            "DF404": "Horizontal shift residuals",
            "DF408": "Vertical shift residuals",
            "DF409": "Iteration limit",
            "DF410": "Number of residuals",
        }
    },
    1023: {
        "name": "Grid residuals (эллипсоидальная ИГД)",
        "description": "Сетка поправок (рестивов) для высот и плановых координат",
        "fields": {
            "DF386": "Message Number",
            "DF387": "Reference-Station ID",
            "DF390": "Source-System ID",
            "DF391": "Target-System ID",
            "DF414": "Number of grid points X",
            "DF415": "Number of grid points Y",
            "DF416": "Grid spacing X (arcsec)",
            "DF417": "Grid spacing Y (arcsec)",
            "DF418": "Grid origin latitude (arcsec)",
            "DF419": "Grid origin longitude (arcsec)",
            "DF420": "Grid name",
            "DF421": "Projection type",
            "DF422": "Residuals (horizontal)",
            "DF423": "Residuals (vertical)",
        }
    },
    1024: {
        "name": "Grid residuals (плоская сетка)",
        "description": "Детальная сеточная модель локальных искажений",
        "fields": {
            "DF386": "Message Number",
            "DF387": "Reference-Station ID",
            "DF390": "Source-System ID",
            "DF391": "Target-System ID",
            "DF414": "Number of grid points X",
            "DF415": "Number of grid points Y",
            "DF416": "Grid spacing X (m)",
            "DF417": "Grid spacing Y (m)",
            "DF418": "Grid origin X (m)",
            "DF419": "Grid origin Y (m)",
            "DF420": "Grid name",
            "DF421": "Projection type",
            "DF422": "Residuals (horizontal)",
            "DF423": "Residuals (vertical)",
        }
    },
    1025: {
        "name": "Projection parameters (общие)",
        "description": "Параметры проекции (кроме Ламберта и Меркатора)",
        "fields": {
            "DF386": "Message Number",
            "DF387": "Reference-Station ID",
            "DF390": "Source-System ID",
            "DF391": "Target-System ID",
            "DF421": "Projection type",
            "DF420": "Projection name",
            "DF427": "Projection parameters",
            "DF424": "Geoid model",
            "DF425": "Geoid separator",
            "DF426": "Geoid undulation",
        }
    },
    1026: {
        "name": "Lambert Conic Conformal (2SP)",
        "description": "Равноугольная коническая проекция Ламберта с двумя стандартными параллелями",
        "fields": {
            "DF386": "Message Number",
            "DF387": "Reference-Station ID",
            "DF390": "Source-System ID",
            "DF391": "Target-System ID",
            "DF420": "Projection name",
            "DF424": "Geoid model",
            "DF425": "Geoid separator",
            "DF426": "Geoid undulation",
            "DF428": "Projection center latitude",
            "DF429": "Projection center longitude",
            "DF430": "Standard parallel 1 latitude",
            "DF431": "Standard parallel 2 latitude",
            "DF432": "False easting",
            "DF433": "False northing",
        }
    },
    1027: {
        "name": "Oblique Mercator",
        "description": "Косоугольная проекция Меркатора",
        "fields": {
            "DF386": "Message Number",
            "DF387": "Reference-Station ID",
            "DF390": "Source-System ID",
            "DF391": "Target-System ID",
            "DF420": "Projection name",
            "DF424": "Geoid model",
            "DF425": "Geoid separator",
            "DF426": "Geoid undulation",
            "DF434": "Projection center latitude",
            "DF435": "Projection center longitude",
            "DF436": "Azimuth of initial line",
            "DF437": "Angle from rectified to skewed grid",
            "DF438": "Scale factor on initial line",
            "DF439": "False easting",
            "DF440": "False northing",
        }
    },
    1300: {
        "name": "CRS Name (source)",
        "description": "Название исходной системы координат",
        "fields": {
            "DF386": "Message Number",
            "DF387": "Reference-Station ID",
            "DF390": "Source-System ID",
            "DF522": "Source CRS name",
        }
    },
    1302: {
        "name": "CRS Name (target)",
        "description": "Название целевой системы координат",
        "fields": {
            "DF386": "Message Number",
            "DF387": "Reference-Station ID",
            "DF391": "Target-System ID",
            "DF523": "Target CRS name",
        }
    },
}
