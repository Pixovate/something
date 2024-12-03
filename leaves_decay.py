# -*- coding: utf-8 -*-
from ...base.IServer import IServer
import mod.server.extraServerApi as serverApi
from collections import defaultdict, deque

ServerSystem = serverApi.GetServerSystemCls()
compFactory = serverApi.GetEngineCompFactory()
levelId = serverApi.GetLevelId()

minecraftEnum = serverApi.GetMinecraftEnum()
playerEnum = minecraftEnum.EntityType.Player

blockInfoComp = compFactory.CreateBlockInfo(levelId)
blockStateComp = compFactory.CreateBlockState(levelId)
blockComp = compFactory.CreateBlock(levelId)
gameComp = compFactory.CreateGame(levelId)


class LeavesServer(IServer):
    def __init__(self, namespace, systemName):
        super(LeavesServer, self).__init__(namespace, systemName)
        self.ListenEvent()
        self.leaves = set(["arkcraft:palm_leaves", "arkcraft:cordaites_leaves"])
        self.logs = set(["arkcraft:palm_log", "arkcraft:cordaites_log"])
        self.spawnResQueue = deque()

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
        if self.spawnResQueue:
            a = self.spawnResQueue.popleft()
            blockInfoComp.SpawnResources(*a)

    def on_block_remove(self, args):
        dimension = args["dimension"]
        sourcePos = (args["x"], args["y"], args["z"])
        if args["fullName"] in self.leaves:
            oriPos = (args["x"] - 1, args["y"] - 1, args["z"] - 1)
            bp = blockComp._paletteHelper._getBlockDescriptionsBetweenPos(
                levelId,
                dimension,
                oriPos,
                (args["x"] + 1, args["y"] + 1, args["z"] + 1),
                False,
            )
            bp_width = bp[3]
            area = bp[4] * bp_width
            mBlockPaletteDescriptionsDict = bp[0]
            for block, index_list in mBlockPaletteDescriptionsDict.items():
                block_name = block[0]
                states = blockStateComp.GetBlockStatesFromAuxValue(block_name, block[1])
                if states is None:
                    continue
                if "vrp:update_bit" in states:
                    states["vrp:update_bit"] = True
                    for index in index_list:
                        y, remainder = divmod(index, area)
                        x, z = divmod(remainder, bp_width)
                        pos = (x + oriPos[0], y + oriPos[1], z + oriPos[2])
                        if pos == sourcePos:
                            continue
                        blockStateComp.SetBlockStates(pos, states, dimension)

        elif args["fullName"] in self.logs:
            oriPos = (args["x"] - 4, args["y"] - 4, args["z"] - 4)
            bp = blockComp._paletteHelper._getBlockDescriptionsBetweenPos(
                levelId,
                dimension,
                oriPos,
                (args["x"] + 4, args["y"] + 4, args["z"] + 4),
                False,
            )
            bp_width = bp[3]
            area = bp[4] * bp_width
            mBlockPaletteDescriptionsDict = bp[0]
            for block, index_list in mBlockPaletteDescriptionsDict.items():
                block_name = block[0]
                states = blockStateComp.GetBlockStatesFromAuxValue(block_name, block[1])
                if states is None:
                    continue
                if "vrp:update_bit" in states:
                    states["vrp:update_bit"] = True
                    for index in index_list:
                        y, remainder = divmod(index, area)
                        x, z = divmod(remainder, bp_width)
                        pos = (x + oriPos[0], y + oriPos[1], z + oriPos[2])
                        blockStateComp.SetBlockStates(pos, states, dimension)

    def random_tick(self, args):
        if self.spawnResQueue:
            a = self.spawnResQueue.popleft()
            blockInfoComp.SpawnResources(*a)
        if args["fullName"] not in self.leaves:
            return

        pos_and_dim = args["posX"], args["posY"], args["posZ"], args["dimensionId"]

        states = blockStateComp.GetBlockStates(pos_and_dim[:3], pos_and_dim[3])
        if states is None:
            return

        update_bit = states.get("vrp:update_bit", False)

        if not update_bit:
            return

        persistent_bit = states.get("vrp:persistent_bit", False)

        if persistent_bit:
            states["vrp:update_bit"] = False
            blockStateComp.SetBlockStates(pos_and_dim[:3], states, pos_and_dim[3])

        search_radius = 4
        size = 2 * search_radius + 1

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

        queue = deque()
        log_set = set()
        leaf_set = set()

        for block, index_list in mBlockPaletteDescriptionsDict.items():
            value = block_types.get(block[0], -1)

            if value == -2:
                leaf_set.update(index_list)
            elif value == 0:
                log_set.update(index_list)

        distances = defaultdict(lambda: 0)
        queue.extend(log_set)

        not_found = True

        center_index = (search_radius * area) + (search_radius * bp_width) + search_radius

        while queue:
            current_index = queue.popleft()
            current_distance = distances[current_index]

            if current_distance >= search_radius:
                continue

            if current_index == center_index:
                not_found = False
                break

            y = current_index // area
            remainder = current_index % area
            x = remainder // bp_width
            z = remainder % bp_width

            for dx, dy, dz in [(-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)]:
                nx, ny, nz = x + dx, y + dy, z + dz
                if 0 <= nx < size and 0 <= ny < size and 0 <= nz < size:
                    neighbor_index = (ny * area) + (nx * bp_width) + nz
                    if neighbor_index in leaf_set and neighbor_index not in distances:
                        manhattan_dist = (
                            abs(nx - search_radius) + abs(ny - search_radius) + abs(nz - search_radius)
                        )
                        if current_distance + 1 + manhattan_dist > search_radius:
                            continue
                        distances[neighbor_index] = current_distance + 1
                        queue.append(neighbor_index)

        if not_found:
            pos = pos_and_dim[:3]
            blockInfoComp.SetBlockNew(pos, {"name": "minecraft:air"}, 0, args["dimensionId"], False, False)
            self.spawnResQueue.append((args["fullName"], pos, 0, 1.0, 0, args["dimensionId"], True))
        else:
            states["vrp:update_bit"] = False
            blockStateComp.SetBlockStates(pos_and_dim[:3], states, pos_and_dim[3])
