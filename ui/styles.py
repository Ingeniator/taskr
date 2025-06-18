from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QStyle
from PySide6.QtGui import QFont, QColor, QPalette

class NoCheckmarkBoldSelectedDelegate(QStyledItemDelegate):
    def initStyleOption(self, option: QStyleOptionViewItem, index):
        super().initStyleOption(option, index)
        option.features &= ~QStyleOptionViewItem.HasCheckIndicator
        if option.state & QStyle.State_Selected:
            option.palette.setColor(QPalette.Text, QColor("#888"))
            option.palette.setColor(QPalette.HighlightedText, QColor("#888"))  # selected+hover
            option.font.setBold(True)