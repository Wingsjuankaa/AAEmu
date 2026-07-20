FROM mcr.microsoft.com/dotnet/sdk:10.0-alpine AS builder
ARG CONFIGURATION=Release

WORKDIR app
COPY ./Directory.Build.props .
COPY ./Directory.Packages.props .
COPY ./AAEmu.Commons ./AAEmu.Commons
COPY ./AAEmu.Login ./AAEmu.Login
RUN dotnet publish ./AAEmu.Login/AAEmu.Login.csproj -c $CONFIGURATION -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:10.0-alpine

RUN apk add --no-cache busybox-extras openssl mysql-client

WORKDIR app

COPY --from=builder /app/publish ./
COPY ./SQL/updates ./SQL/updates

RUN mkdir -p /app/Logs && chown -R app:app /app

ENV DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1

EXPOSE 1234 1237
USER app
ENTRYPOINT ["dotnet", "AAEmu.Login.dll"]
