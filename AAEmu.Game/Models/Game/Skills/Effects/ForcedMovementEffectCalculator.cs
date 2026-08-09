using System;
using System.Numerics;

namespace AAEmu.Game.Models.Game.Skills.Effects
{
    /// <summary>
    /// Pure AA8 forced-movement calculations. KnockBack stores its magnitude in
    /// millimetres and its elevation in degrees. PhysicalExplosion is a
    /// CryEngine pe_explosion envelope: AA supplies rmin == rmax == radius, so
    /// pressure is constant inside the radius and zero outside it.
    /// </summary>
    public static class ForcedMovementEffectCalculator
    {
        public static Vector3 CalculateKnockBackDisplacement(
            Vector3 casterPosition,
            Vector3 targetPosition,
            int magnitudeMillimetres,
            int elevationDegrees)
        {
            if (magnitudeMillimetres <= 0)
                return Vector3.Zero;

            var magnitudeMetres = magnitudeMillimetres / 1000f;
            var elevationRadians = elevationDegrees * Math.PI / 180d;
            var horizontalMagnitude = magnitudeMetres * (float)Math.Cos(elevationRadians);
            var verticalMagnitude = magnitudeMetres * (float)Math.Sin(elevationRadians);

            var away = new Vector2(
                targetPosition.X - casterPosition.X,
                targetPosition.Y - casterPosition.Y);
            if (away.LengthSquared() < 0.000001f)
                away = Vector2.UnitY;
            else
                away = Vector2.Normalize(away);

            return new Vector3(
                away.X * horizontalMagnitude,
                away.Y * horizontalMagnitude,
                verticalMagnitude);
        }

        public static float CalculateExplosionPressure(float distance, float radius, float pressure)
        {
            if (radius <= 0f || distance < 0f || distance > radius)
                return 0f;

            return pressure;
        }
    }
}
