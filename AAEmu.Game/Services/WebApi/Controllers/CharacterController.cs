using System.Text;
using AAEmu.Commons.Utils.DB;
using System.Text.RegularExpressions;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Services.WebApi.Models;
using NetCoreServer;

namespace AAEmu.Game.Services.WebApi.Controllers;

internal class CharacterController : BaseController
{
    [WebApiGet("/api/character/list")]
    public HttpResponse List(HttpRequest request)
    {
        var queryParams = ParseQueryString(request.Url);
        var list = new List<CharacterModel>();
        using (var connection = MySQL.CreateConnection())
        {
            using (var command = connection.CreateCommand())
            {
                // Build SQL
                var sqlBuilder =
                    new StringBuilder(
                        "SELECT `id`, `name`, `level`,`created_at`, `account_id` FROM `characters` WHERE `deleted` = 0");

                var accountId = queryParams.Get("AccountId");
                if (accountId != null)
                {
                    sqlBuilder.Append(" AND `account_id` = @accountId");
                    command.Parameters.AddWithValue("@accountId", accountId);
                }

                var name = queryParams.Get("Name");
                if (name != null)
                {
                    sqlBuilder.Append(" AND `name` = @name");
                    command.Parameters.AddWithValue("@name", name);
                }

                command.CommandText = sqlBuilder.ToString();
                command.Prepare();
                using (var reader = command.ExecuteReader())
                {
                    while (reader.Read())
                    {
                        var id = reader.GetUInt32("id");
                        var charName = reader.GetString("name");
                        var createdAt = reader.GetDateTime("created_at");
                        var character = WorldManager.Instance.GetCharacterById(id);

                        var level = reader.GetUInt32("level");

                        if (character != null)
                        {
                            level = character.Level;
                        }

                        list.Add(new CharacterModel(id, charName, level, createdAt, character != null));
                    }
                }
            }
        }

        return OkJson(list);
    }

    [WebApiGet("/api/character/([0-9]+)/inventory")]
    public HttpResponse Inventory(HttpRequest request, MatchCollection matches)
    {
        if (!uint.TryParse(matches[0].Groups[1].Value, out var characterId))
            return BadRequestJson(new ErrorModel("Invalid character id"));

        string characterName = null;
        uint level = 0;

        using (var connection = MySQL.CreateConnection())
        using (var command = connection.CreateCommand())
        {
            command.CommandText =
                "SELECT `name`, `level` FROM `characters` WHERE `id` = @characterId AND `deleted` = 0 LIMIT 1";
            command.Parameters.AddWithValue("@characterId", characterId);
            command.Prepare();

            using var reader = command.ExecuteReader();
            if (!reader.Read())
                return BadRequestJson(new ErrorModel($"Character {characterId} not found"));

            characterName = reader.GetString("name");
            level = reader.GetUInt32("level");
        }

        var onlineCharacter = WorldManager.Instance.GetCharacterById(characterId);
        if (onlineCharacter != null)
        {
            characterName = onlineCharacter.Name;
            level = onlineCharacter.Level;
        }

        var equipment = ItemManager.Instance.FindItemContainerFor(characterId, SlotType.Equipment, 0);
        var backpack = ItemManager.Instance.FindItemContainerFor(characterId, SlotType.Inventory, 0);
        var snapshot = CharacterInventorySnapshotModel.Create(
            characterId,
            characterName,
            level,
            onlineCharacter != null,
            equipment,
            backpack,
            DateTime.UtcNow);

        return OkJson(snapshot);
    }
}
