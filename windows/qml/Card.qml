import QtQuick
import AppTheme 1.0

// Shared surface (spec Layer 1): rounded body + hairline border.
Rectangle {
    color: Theme.surface
    radius: Theme.radius
    border.width: 1
    border.color: Theme.border
}
