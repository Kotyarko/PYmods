from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from gui import DialogsInterface
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.lobby.customization.customization_inscription_controller import PersonalNumEditCommands
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView as WGMainView
from gui.Scaleform.daapi.view.lobby.customization.shared import SEASONS_ORDER, getTotalPurchaseInfo, containsVehicleBound
from gui.Scaleform.genConsts.CUSTOMIZATION_DIALOGS import CUSTOMIZATION_DIALOGS
from gui.shared import events, EVENT_BUS_SCOPE
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.gui_items.gui_item_economics import ITEM_PRICE_EMPTY
from items.components.c11n_constants import SeasonType
from .. import g_config


class MainView(WGMainView):
    def showBuyWindow(self, ctx=None):  # TODO: teach this not to by CamoSelector's stuff
        if self.__ctx.isOnly1ChangedNumberInEditMode():
            self.__ctx.sendNumberEditModeCommand(PersonalNumEditCommands.FINISH_BY_CLICK)
        elif self.__ctx.numberEditModeActive:
            self.__ctx.sendNumberEditModeCommand(PersonalNumEditCommands.CANCEL_EDIT_MODE)
        if not self.__ctx.numberEditModeActive:
            self.changeVisible(False)
            purchaseItems = self.__ctx.getPurchaseItems()
            cart = getTotalPurchaseInfo(purchaseItems)
            if cart.totalPrice == ITEM_PRICE_EMPTY:
                if containsVehicleBound(purchaseItems):
                    DialogsInterface.showI18nConfirmDialog(
                        CUSTOMIZATION_DIALOGS.CUSTOMIZATION_INSTALL_BOUND_CHECK_NOTIFICATION, self.onBuyConfirmed)
                else:
                    self.__ctx.applyItems(purchaseItems)
            else:
                self.fireEvent(events.LoadViewEvent(VIEW_ALIAS.CUSTOMIZATION_PURCHASE_WINDOW, ctx=ctx), EVENT_BUS_SCOPE.LOBBY)

    def __setNotificationCounters(self):
        currentSeason = self.__ctx.currentSeason
        newItems = g_currentVehicle.item.getNewC11nItems(g_currentVehicle.itemsCache.items)
        seasonCounters = {season: 0 for season in SEASONS_ORDER}
        if self.__ctx.isBuy:
            itemTypes = GUI_ITEM_TYPE.CUSTOMIZATIONS
        else:
            itemTypes = ()
        for item in newItems:
            if item.season != SeasonType.ALL and item.itemTypeID in itemTypes and not item.season & currentSeason:
                seasonCounters[item.season] += 1

        self.as_setNotificationCountersS([seasonCounters[season] for season in SEASONS_ORDER])


@overrideMethod(WGMainView, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(MainView, *a, **kw)
