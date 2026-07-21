FROM mcr.microsoft.com/dotnet/sdk:3.1.409-focal as builder
ARG CONFIGURATION
ARG RUNTIME

WORKDIR app
COPY ./AAEmu.Commons ./AAEmu.Commons
COPY ./AAEmu.Game ./AAEmu.Game
RUN dotnet publish ./AAEmu.Game/AAEmu.Game.csproj -c $CONFIGURATION -r $RUNTIME --self-contained true

FROM ubuntu:20.04
ARG CONFIGURATION
ARG FRAMEWORK
ARG RUNTIME
ARG LOGIN_HOST
ARG LOGIN_PORT
ARG DB_HOST
ARG DB_PORT
ARG DB_USER
ARG DB_PASSWORD
ARG GAME_PORT
ARG STREAM_PORT

RUN apt update && apt install openssl -y
WORKDIR app
COPY --from=builder app/AAEmu.Game/bin/$CONFIGURATION/$FRAMEWORK/$RUNTIME/publish ./
RUN cp ./ExampleConfig.json ./Config.json
RUN sed -i "s/%login_host%/$LOGIN_HOST/" ./Config.json
RUN sed -i "s/%login_port%/$LOGIN_PORT/" ./Config.json
RUN sed -i "s/%db_host%/$DB_HOST/" ./Config.json
RUN sed -i "s/%db_port%/$DB_PORT/" ./Config.json
RUN sed -i "s/%db_user%/$DB_USER/" ./Config.json
RUN sed -i "s/%db_password%/$DB_PASSWORD/" ./Config.json
RUN sed -i "s/%game_port%/$GAME_PORT/" ./Config.json
RUN sed -i "s/%stream_port%/$STREAM_PORT/" ./Config.json

EXPOSE $GAME_PORT $STREAM_PORT
ENTRYPOINT ["./AAEmu.Game"]
