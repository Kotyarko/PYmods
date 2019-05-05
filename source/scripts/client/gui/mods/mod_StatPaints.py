__appID__ = '216060d4797ff99153c400922baeed6f'
import BigWorld
import json
import threading
import traceback
import urllib2
from ClientArena import ClientArena
from PYmodsCore import PYmodsConfigInterface, Analytics, overrideMethod
from functools import partial
from gui.Scaleform.battle_entry import BattleEntry
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.gui_items.customization.c11n_items import Paint
from items.vehicles import g_cache
from vehicle_systems.CompoundAppearance import CompoundAppearance
from vehicle_systems.tankStructure import TankPartNames


class ConfigInterface(PYmodsConfigInterface):
    def __init__(self):
        self.dossier = {}
        self.pending = set()
        self.attempts = {}
        self.failed = set()
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.1.0 (%(file_compile_date)s)'
        self.data = {'enabled': True,
                     'player': True,
                     'ally': True,
                     'enemy': True,
                     'ignorePresentPaints': False,
                     'removeCamouflages': True,
                     'paint_chassis': False,
                     'paint_hull': False,
                     'paint_turret': True,
                     'paint_gun': True,
                     'scale': {'2020': 264, '4185': 225, '6340': 203, '8525': 224, '9930': 204, '99999': 200}}
        self.i18n = {
            'UI_description': 'Statistics vehicle painter',
            'UI_setting_ignorePresentPaints_text': 'Ignore present paints',
            'UI_setting_ignorePresentPaints_tooltip':
                'Enable - vehicles will be coloured into stat colors ignoring present paints or styles.\n'
                'Disable - if a vehicle has a paint or style applied to it - it will be kept.',
            'UI_setting_colorScales_text': 'Color scales are edited via config file.',
            'UI_setting_removeCamouflages_text': 'Remove camouflages before repainting',
            'UI_setting_removeCamouflages_tooltip': 'Remove camouflages from the parts which will be recolored.',
            'UI_setting_teams_text': 'These vehicles will be painted:',
            'UI_setting_player_text': 'Player',
            'UI_setting_ally_text': 'Allies',
            'UI_setting_enemy_text': 'Enemies',
            'UI_setting_parts_text': 'These vehicle parts will be painted:',
            'UI_setting_paint_chassis_text': 'Chassis',
            'UI_setting_paint_hull_text': 'Hulls',
            'UI_setting_paint_turret_text': 'Turrets',
            'UI_setting_paint_gun_text': 'Guns'}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        return {'modDisplayName': self.i18n['UI_description'],
                'enabled': self.data['enabled'],
                'column1': [
                    self.tb.createControl('ignorePresentPaints'),
                    self.tb.createControl('removeCamouflages'),
                    self.tb.createLabel('teams'),
                    self.tb.createControl('player'),
                    self.tb.createControl('ally'),
                    self.tb.createControl('enemy')
                ],
                'column2': [
                    self.tb.createLabel('parts'),
                    self.tb.createControl('paint_chassis'),
                    self.tb.createControl('paint_hull'),
                    self.tb.createControl('paint_turret'),
                    self.tb.createControl('paint_gun'),
                    self.tb.createLabel('colorScales')
                ]}

    def loadPlayerStats(self, databaseIDs):
        regions = {}
        for databaseID in databaseIDs:
            if databaseID not in self.pending and databaseID not in self.dossier and databaseID not in self.failed:
                if databaseID not in self.attempts:
                    self.attempts[databaseID] = 0
                self.attempts[databaseID] += 1
                if self.attempts[databaseID] > 100:
                    print self.ID + ': could not load info for databaseID', databaseID
                    self.failed.add(databaseID)
                    del self.attempts[databaseID]
                    continue
                self.pending.add(databaseID)
                regions.setdefault(userRegion(int(databaseID)), []).append(databaseID)
        results = []
        for region in regions:
            try:
                results.append(json.loads(urllib2.urlopen((
                    'https://api.worldoftanks.{'
                    'region}/wot/account/info/?application_id={aid}&fields=global_rating&account_id={id}').format(
                    region=region, id=','.join(regions[region]), aid=__appID__)).read()).get('data', None))
            except IOError:
                for databaseID in regions[region]:
                    self.pending.discard(databaseID)
        for result in results:
            if result:
                for databaseID in result:
                    dossier = result[databaseID]
                    self.dossier[databaseID] = {'wgr': dossier['global_rating']}
                    self.pending.discard(databaseID)
        for databaseID in databaseIDs:
            self.pending.discard(databaseID)
        BigWorld.callback(0, partial(self.updatePaints, databaseIDs))

    def updatePaints(self, databaseIDs):
        player = BigWorld.player()
        if not hasattr(player, 'guiSessionProvider'):
            return BigWorld.callback(1, partial(self.updatePaints, databaseIDs))
        for databaseID in databaseIDs:
            vehicleID = player.guiSessionProvider.getCtx().getArenaDP().getVehIDByAccDBID(int(databaseID))
            vehicle = BigWorld.entity(vehicleID)
            if vehicle is not None and vehicle.appearance is not None:
                vehicle.appearance.setVehicle(vehicle)

    def thread(self, databaseIDs):
        try:
            databaseIDs = [x for x in databaseIDs if x not in self.pending and x not in self.failed]
            if databaseIDs:
                thread = threading.Thread(target=self.loadPlayerStats, args=(databaseIDs,))
                thread.setDaemon(True)
                thread.start()
        except StandardError:
            traceback.print_exc()

    def loadStats(self):
        arena = BigWorld.player().arena
        if arena is not None and arena.bonusType != 6:  # If it isn't tutorial battle
            self.thread([str(pl['accountDBID']) for pl in arena.vehicles.values()])

    def resetStats(self):
        self.attempts.clear()
        self.dossier.clear()
        self.pending.clear()


def userRegion(databaseID):
    if databaseID < 500000000:
        return 'ru'
    if databaseID < 1000000000:
        return 'eu'
    if databaseID < 2000000000:
        return 'na'
    return 'asia'


g_config = ConfigInterface()
analytics = Analytics(g_config.ID, g_config.version, 'UA-76792179-15')


@overrideMethod(ClientArena, '_ClientArena__onVehicleListUpdate')
def new__onVehicleListUpdate(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    g_config.loadStats()


@overrideMethod(BattleEntry, 'beforeDelete')
def new_BattleEntry_beforeDelete(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    g_config.resetStats()


@overrideMethod(CompoundAppearance, '_CompoundAppearance__applyVehicleOutfit')
def new_applyVehicleOutfit(base, self, *a, **kw):
    outfit = self.outfit
    vID = self.id
    vDesc = self.typeDescriptor
    if not vDesc or not g_config.data['enabled']:
        return base(self, *a, **kw)
    player = BigWorld.player()
    isPlayer = vID == player.playerVehicleID
    isAlly = player.arena.vehicles[vID]['team'] == player.team
    if not (g_config.data['player'] if isPlayer else g_config.data['ally'] if isAlly else g_config.data['enemy']):
        return base(self, *a, **kw)
    fashions = self._CompoundAppearance__fashions
    paintItems = {}
    paints = g_cache.customization20().paints
    for paintID in g_config.data['scale'].itervalues():
        paintItem = Paint(paints[paintID].compactDescr)
        if not paintItem.descriptor.matchVehicleType(vDesc.type):
            return base(self, *a, **kw)
        paintItems[paintID] = paintItem
    accountID = str(player.arena.vehicles[vID]['accountDBID'])
    if accountID not in g_config.dossier:
        if accountID not in g_config.pending:
            g_config.thread([accountID])
        return base(self, *a, **kw)
    paintID = None
    rating = g_config.dossier[accountID]['wgr']
    for value in sorted(int(x) for x in g_config.data['scale']):
        if rating < value:
            paintID = g_config.data['scale'][str(value)]
            break
    for fashionIdx, descId in enumerate(TankPartNames.ALL):
        if not g_config.data['paint_%s' % descId]:
            continue
        removeCamo = False
        container = outfit.getContainer(fashionIdx)
        paintSlot = container.slotFor(GUI_ITEM_TYPE.PAINT)
        camoSlot = container.slotFor(GUI_ITEM_TYPE.CAMOUFLAGE)
        if paintSlot is not None:
            for idx in xrange(paintSlot.capacity()):
                if g_config.data['ignorePresentPaints'] or paintSlot.getItem(idx) is None:
                    paintSlot.set(paintItems[paintID], idx)
                    removeCamo = True
        if camoSlot is not None:
            if g_config.data['removeCamouflages'] and removeCamo:
                camoSlot.clear()
                fashion = fashions[fashionIdx]
                if fashion is None:
                    continue
                fashion.removeCamouflage()
    self._CompoundAppearance__outfit = outfit
    base(self, *a, **kw)
