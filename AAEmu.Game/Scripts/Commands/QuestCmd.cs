using System.Collections.Generic;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Utils;

namespace AAEmu.Game.Scripts.Commands
{
    public class QuestCmd : ICommand
    {
        public void OnLoad()
        {
            CommandManager.Instance.Register( "quest", this );
        }

        public string GetCommandLineHelp()
        {
            return "<diagnose||try||force||sync||list||add||remove||prog||reward>";
        }

        public string GetCommandHelpText()
{
            return "[Quest] /quest <diagnose/try/force/sync/add/remove/list/prog/reward>";
        }

        public void Execute( Character character, string[] args )
        {
            if ( args.Length < 1 )
            {
                character.SendMessage( "[Quest] /quest <diagnose/try/force/sync/add/remove/list/prog/reward>" );
                return;
            }

            QuestCommandUtil.GetCommandChoice( character, args[0], args );
        }
    }
}
