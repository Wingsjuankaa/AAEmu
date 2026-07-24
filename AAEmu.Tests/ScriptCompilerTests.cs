using System;
using System.Reflection;

using AAEmu.Game.Utils.Scripts;

using Xunit;

namespace AAEmu.Tests
{
    public class ScriptCompilerTests
    {
        [Fact]
        public void ScriptDiscoveryRejectsGeneratedAndNonInstantiableTypes()
        {
            Assert.True(IsLoadable(typeof(ScriptCompilerLoadableFixture)));
            Assert.False(IsLoadable(typeof(AbstractScript)));
            Assert.False(IsLoadable(typeof(StaticCompilerDetail)));
            Assert.False(IsLoadable(typeof(NoDefaultConstructor)));
        }

        private static bool IsLoadable(Type type)
        {
            var method = typeof(ScriptCompiler).GetMethod(
                "IsLoadableScriptType",
                BindingFlags.Static | BindingFlags.NonPublic);

            Assert.NotNull(method);
            return (bool)method.Invoke(null, new object[] { type });
        }

        private abstract class AbstractScript
        {
        }

        private static class StaticCompilerDetail
        {
        }

        private sealed class NoDefaultConstructor
        {
            public NoDefaultConstructor(int value)
            {
            }
        }
    }

    internal sealed class ScriptCompilerLoadableFixture
    {
        public ScriptCompilerLoadableFixture()
        {
        }
    }
}
