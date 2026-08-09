using System;
using System.Collections.Generic;

using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.DoodadObj;

using Xunit;

namespace AAEmu.Tests
{
    public class DoodadSerializationTests
    {
        [Fact]
        public void KakaoEightCreatedDoodadWritesUpdatedTimeBeforeTrailingTypes()
        {
            const int data = 0x12345678;
            var doodad = new Doodad
            {
                Data = data,
                Flag = 0
            };
            var stream = new PacketStream();

            doodad.Write(stream);

            var expectedTail = new List<byte>();
            expectedTail.AddRange(BitConverter.GetBytes(data));  // data
            expectedTail.AddRange(BitConverter.GetBytes(data));  // data2
            expectedTail.AddRange(BitConverter.GetBytes(0UL));   // updatedTime
            expectedTail.AddRange(BitConverter.GetBytes(0u));    // type
            expectedTail.AddRange(BitConverter.GetBytes(0u));    // type

            var actualTail = stream.GetBytes()[^expectedTail.Count..];
            Assert.Equal(expectedTail, actualTail);
        }
    }
}
