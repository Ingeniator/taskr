from PyQt5.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import QStyle

class NoCheckmarkBoldSelectedDelegate(QStyledItemDelegate):
    def initStyleOption(self, option: QStyleOptionViewItem, index):
        super().initStyleOption(option, index)
        option.features &= ~QStyleOptionViewItem.HasCheckIndicator
        if option.state & QStyle.State_Selected:
            option.palette.setColor(option.palette.Text, QColor("#888"))
            option.palette.setColor(option.palette.HighlightedText, QColor("#888"))  # selected+hover
            option.font.setBold(True)