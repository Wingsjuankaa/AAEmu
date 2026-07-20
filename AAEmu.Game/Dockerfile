FROM mcr.microsoft.com/dotnet/sdk:10.0 AS builder
ARG CONFIGURATION=Release

RUN apt-get update \
    && apt-get install --yes --no-install-recommends xz-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR app
COPY ./Directory.Build.props .
COPY ./Directory.Packages.props .
COPY ./AAEmu.Commons ./AAEmu.Commons
COPY ./AAEmu.Game ./AAEmu.Game
RUN dotnet publish ./AAEmu.Game/AAEmu.Game.csproj -c $CONFIGURATION -o /app/publish

FROM mcr.microsoft.com/dotnet/runtime:10.0

RUN apt-get update \
    && apt-get install --yes --no-install-recommends default-mysql-client netcat-openbsd openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR app
COPY --from=builder /app/publish ./
COPY ./SQL/updates ./SQL/updates

RUN mkdir -p /app/Logs && chown -R app:app /app

ENV DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1

EXPOSE 1239 1250
USER app
ENTRYPOINT ["dotnet", "AAEmu.Game.dll"]
