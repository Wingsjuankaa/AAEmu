FROM mcr.microsoft.com/dotnet/sdk:10.0-alpine AS builder
ARG CONFIGURATION=Debug

RUN apk add --no-cache xz

WORKDIR /src
COPY ./Directory.Build.props .
COPY ./Directory.Packages.props .
COPY ./AAEmu.Commons ./AAEmu.Commons
COPY ./AAEmu.Game ./AAEmu.Game
COPY ./AAEmu.WorldServer ./AAEmu.WorldServer

# AAEmu.World hosts AAEmu.Game in-process. Keep a separate Game publish tree because
# World switches FileManager.AppPath to GameContentRoot before starting the CS/SC server.
RUN dotnet publish ./AAEmu.Game/AAEmu.Game.csproj -c "$CONFIGURATION" -o /publish/game
# World references Game and both projects intentionally carry Config.json/NLog.config.
# `publish` flattens those linked files and rejects the duplicate relative paths;
# a framework-dependent build preserves the World host output we need here.
RUN dotnet build ./AAEmu.WorldServer/AAEmu.World/AAEmu.World.csproj -c "$CONFIGURATION" -o /publish/world

FROM mcr.microsoft.com/dotnet/runtime:10.0-alpine

RUN apk add --no-cache openssl mysql-client

WORKDIR /app
COPY --from=builder /publish/world ./
COPY --from=builder /publish/game ./game/

EXPOSE 1239 1240 1250
ENTRYPOINT ["dotnet", "AAEmu.World.dll"]
