# Playit Alpha — 2026-09-25

Configurados y desplegados tres canales TCP públicos en un único túnel Brasil: `laurel-filmed.tun.ply.gg:49172–49174`, IPv4 `198.22.204.17`. Destinos loopback `12370–12372` → Login1237/Game1239/Stream1250.

Se añadió `StreamNetwork.AdvertisedPort`, con fallback al puerto local para preservar LAN. La configuración está persistida como override Compose y en el perfil activo de Control Center. Simple Launcher local actualizado; ZIP de configuración preparado para el otro PC.

Gates: restore/build Release y 5.667 tests correctos. Login/Game saludables, Quest Strict findings=0. Tres pruebas TCP públicas corroboradas en logs del backend. La sesión retail desde otra red sigue pendiente; no se han operado Zones.

Detalles, limitaciones y rollback: [AA10PlayitAlpha_es.md](../../Docs/AA10PlayitAlpha_es.md). Evidencia: `E:/AAEmu/rama_10/artifacts/playit/20260925`. Imagen `sha256:8c8e09683108d90b54da9940f5b26d482203f8768a7e309f9c9c78c92af366d3`. HEAD base `1c724fccc84580ba975233b3419b4deb939b6b24`, rama `rama_10`, padre declarado `upstream/client_version/zone-10.0.2_r575`.
