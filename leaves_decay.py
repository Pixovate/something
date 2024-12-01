# -*- coding: utf-8 -*-
from ...base.IServer import IServer
import mod.server.extraServerApi as serverApi
from collections import deque

ServerSystem = serverApi.GetServerSystemCls()
compFactory = serverApi.GetEngineCompFactory()
levelId = serverApi.GetLevelId()

minecraftEnum = serverApi.GetMinecraftEnum()
playerEnum = minecraftEnum.EntityType.Player

blockInfoComp = compFactory.CreateBlockInfo(levelId)
blockStateComp = compFactory.CreateBlockState(levelId)
gameComp = compFactory.CreateGame(levelId)


class LeavesServer(IServer):
    def __init__(self, namespace, systemName):
        super(LeavesServer, self).__init__(namespace, systemName)
        self.ListenEvent()
        self.leaves = set(["arkcraft:palm_leaves"])
        self.logs = set(["arkcraft:palm_log"])
        self.updateBitSet = set()

        blockInfoComp.ListenOnBlockRemoveEvent("arkcraft:palm_leaves", True)
        blockInfoComp.ListenOnBlockRemoveEvent("arkcraft:palm_log", True)

    @staticmethod
    def getModName():
        return "ArkCraft"

    @staticmethod
    def getClientName():
        return "LeavesBlock"

    def ListenEvent(self):
        self.RegisterVanillaEvent("BlockRandomTickServerEvent", self.random_tick)
        self.RegisterVanillaEvent("BlockRemoveServerEvent", self.on_block_remove)
        self.RegisterVanillaEvent("OnScriptTickServer", self.on_script_tick)

    def on_script_tick(self):
        if self.updateBitSet:
            block = next(iter(self.updateBitSet))
            if blockInfoComp.GetBlockNew(block[:3], block[3]).get("name") not in self.leaves:
                self.updateBitSet.remove(block)

    def on_block_remove(self, args):
        if args["fullName"] in self.leaves:
            for dx in xrange(-1, 2):
                for dy in xrange(-1, 2):
                    for dz in xrange(-1, 2):
                        self.updateBitSet.add(
                            (args["x"] + dx, args["y"] + dy, args["z"] + dz, args["dimension"])
                        )

        elif args["fullName"] in self.logs:
            for dx in xrange(-4, 5):
                for dy in xrange(-4, 5):
                    for dz in xrange(-4, 5):
                        self.updateBitSet.add(
                            (args["x"] + dx, args["y"] + dy, args["z"] + dz, args["dimension"])
                        )

    def random_tick(self, args):
        if args["fullName"] not in self.leaves:
            return

        pos_and_dim = args["posX"], args["posY"], args["posZ"], args["dimensionId"]

        if pos_and_dim not in self.updateBitSet:
            return

        search_radius = 4
        size = 2 * search_radius + 1

        distances = {}
        queue = deque()

        bp = compFactory.CreateBlock(levelId)._paletteHelper._getBlockDescriptionsBetweenPos(
            levelId,
            args["dimensionId"],
            (
                pos_and_dim[0] - search_radius,
                pos_and_dim[1] - search_radius,
                pos_and_dim[2] - search_radius,
            ),
            (
                pos_and_dim[0] + search_radius,
                pos_and_dim[1] + search_radius,
                pos_and_dim[2] + search_radius,
            ),
            False,
        )

        bp_width = bp[3]
        area = bp[4] * bp_width
        logs = self.logs
        leaves = self.leaves
        mBlockPaletteDescriptionsDict = bp[0]

        block_types = {name: 0 for name in logs}
        block_types.update({name: -2 for name in leaves})

        for block, index_list in mBlockPaletteDescriptionsDict.items():
            block_name = block[0]
            value = block_types.get(block_name, -1)
            is_log = value == 0

            for index in index_list:
                y, remainder = divmod(index, area)
                x, z = divmod(remainder, bp_width)
                pos = (x, y, z)
                distances[pos] = value
                if is_log:
                    queue.append(pos)

        while queue:
            x, y, z = queue.popleft()
            current_distance = distances[(x, y, z)]
            if current_distance >= search_radius:
                continue

            for dx, dy, dz in [(-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)]:
                nx, ny, nz = x + dx, y + dy, z + dz
                neighbor_key = (nx, ny, nz)
                if 0 <= nx < size and 0 <= ny < size and 0 <= nz < size:
                    if distances.get(neighbor_key) == -2:
                        distances[neighbor_key] = current_distance + 1
                        queue.append(neighbor_key)

        center_key = (search_radius, search_radius, search_radius)
        if distances.get(center_key, -1) < 0:
            pos = pos_and_dim[:3]
            blockInfoComp.SetBlockNew(pos, {"name": "minecraft:air"}, 0, args["dimensionId"], False, False)
            # blockInfoComp.SpawnResources(args["fullName"], pos, 0, 1.0, 0, args["dimensionId"], True)
        self.updateBitSet.remove(pos_and_dim)
