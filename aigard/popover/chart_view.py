"""
折线图视图 - 使用 Core Graphics 绘制 Token 历史趋势
"""
import objc
from AppKit import NSView, NSColor, NSBezierPath
from Foundation import NSMakePoint


class LineChartView(NSView):
    """折线图视图"""

    def initWithFrame_(self, frame):
        """标准初始化方法"""
        self = objc.super(LineChartView, self).initWithFrame_(frame)
        if self is None:
            return None

        self.data = []
        print(f"LineChartView 初始化成功: frame={frame}")
        return self

    def drawRect_(self, rect):
        """绘制折线图"""
        bounds = self.bounds()
        width = bounds.size.width
        height = bounds.size.height

        # 绘制背景 (半透明白色)
        NSColor.colorWithWhite_alpha_(1.0, 0.1).setFill()
        NSBezierPath.fillRect_(bounds)

        # 如果没有数据,显示占位文本
        if not self.data or len(self.data) < 2:
            print(f"折线图没有数据: data={self.data}")
            return

        print(f"绘制折线图: {len(self.data)} 个数据点")

        # 计算数据范围
        values = [y for x, y in self.data]
        min_val = min(values)
        max_val = max(values)
        value_range = max_val - min_val if max_val > min_val else 1

        # 绘制折线
        path = NSBezierPath.bezierPath()
        path.setLineWidth_(2.0)

        for i, (x, y) in enumerate(self.data):
            # 归一化坐标
            norm_x = (i / (len(self.data) - 1)) * (width - 10) + 5
            norm_y = ((y - min_val) / value_range) * (height - 20) + 10

            if i == 0:
                path.moveToPoint_(NSMakePoint(norm_x, norm_y))
            else:
                path.lineToPoint_(NSMakePoint(norm_x, norm_y))

        # 设置颜色并绘制
        NSColor.systemBlueColor().setStroke()
        path.stroke()

    def setData_(self, data):
        """更新数据并重绘"""
        self.data = data if data else []
        print(f"折线图数据已更新: {len(self.data)} 个数据点")
        self.setNeedsDisplay_(True)
