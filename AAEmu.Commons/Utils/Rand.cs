using System;

namespace AAEmu.Commons.Utils
{
    public class Rand
    {
        private static MersenneTwister _random = new MersenneTwister(DateTime.UtcNow.Millisecond);
        private static object _lock = new object();

        /// <summary>
        /// Installs a deterministic generator for an isolated mechanics run and
        /// restores the previous generator when the returned scope is disposed.
        /// Production callers never enter this scope and retain the historical
        /// time-seeded generator.
        /// </summary>
        public static IDisposable PushDeterministicSeed(int seed)
        {
            lock (_lock)
            {
                var previous = _random;
                _random = new MersenneTwister(seed);
                return new RandomScope(previous);
            }
        }

        public static int Next()
        {
            lock (_lock)
            {
                return _random.Next();
            }
        }

        public static int Next(int maxValue)
        {
            lock (_lock)
            {
                return _random.Next(maxValue);
            }
        }

        public static int Next(int minValue, int maxValue)
        {
            lock (_lock)
            {
                return _random.Next(minValue, maxValue);
            }
        }

        public static double NextDouble()
        {
            lock (_lock)
            {
                return _random.NextDouble(true);
            }
        }

        public static float NextSingle()
        {
            lock (_lock)
            {
                return _random.NextSingle(true);
            }
        }

        public static float Next(float maxValue)
        {
            lock (_lock)
            {
                return _random.NextSingle(true) * maxValue;
            }
        }

        public static float Next(float minValue, float maxValue)
        {
            lock (_lock)
            {
                return _random.NextSingle(true) * (maxValue - minValue) + minValue;
            }
        }

        private sealed class RandomScope : IDisposable
        {
            private MersenneTwister _previous;

            public RandomScope(MersenneTwister previous)
            {
                _previous = previous;
            }

            public void Dispose()
            {
                lock (_lock)
                {
                    if (_previous == null)
                        return;
                    _random = _previous;
                    _previous = null;
                }
            }
        }
    }
}
