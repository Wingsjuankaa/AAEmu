using System;

namespace AAEmu.Game.Models.Game.NPChar
{
    public static class NpcSpawnHeightPolicy
    {
        public const float MaximumTerrainCorrection = 1f;

        public static float Resolve(float sourceHeight, float terrainHeight, bool hasHeightMap, bool canFly)
        {
            if (!hasHeightMap || canFly)
                return sourceHeight;

            return Math.Abs(sourceHeight - terrainHeight) < MaximumTerrainCorrection
                ? terrainHeight
                : sourceHeight;
        }
    }
}
