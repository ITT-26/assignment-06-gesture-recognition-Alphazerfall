# $1 gesture recognizer, closely based on the pseudocode by Wobbrock et al.
# https://depts.washington.edu/acelab/proj/dollar/dollar.pdf

import math

PHI = 0.5 * (-1.0 + math.sqrt(5.0))


class Recognizer:
    def __init__(self, templates):
        self.templates = templates

    def _distance(self, p1, p2):
        return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)**0.5

    def _centroid(self, points):
        return (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))

    def _bounding_box(self, points):
        xs, ys = zip(*points)
        return min(xs), max(xs), min(ys), max(ys)

    def resample(self, points, n):
        interval = self.path_length(points) / (n - 1)
        d = 0.0
        newPoints = [points[0]]
        i = 1
        while i < len(points):
            dist = self._distance(points[i - 1], points[i])
            if d + dist >= interval:
                qx = points[i-1][0] + ((interval - d) / dist) * (points[i][0] - points[i-1][0])
                qy = points[i-1][1] + ((interval - d) / dist) * (points[i][1] - points[i-1][1])
                q = (qx, qy)
                newPoints.append(q)
                points.insert(i, q)
                d = 0.0
            else:
                d += dist
            i += 1
        if len(newPoints) == n - 1:
            newPoints.append(points[-1])
        return newPoints

    def path_length(self, points):
        d = 0.0
        for i in range(1, len(points)):
            d += self._distance(points[i-1], points[i])
        return d

    def path_distance(self, a, b):
        d = 0.0
        for i in range(0, len(a)):
            d += self._distance(a[i], b[i])
        return d / len(a)

    def indicative_angle(self, points):
        c = self._centroid(points)
        return math.atan2(c[1] - points[0][1], c[0] - points[0][0])

    def rotate_by(self, points, w):
        c = self._centroid(points)
        newPoints = []
        for p in points:
            qx = (p[0] - c[0]) * math.cos(w) - (p[1] - c[1]) * math.sin(w) + c[0]
            qy = (p[0] - c[0]) * math.sin(w) + (p[1] - c[1]) * math.cos(w) + c[1]
            newPoints.append((qx, qy))
        return newPoints

    def scale_to(self, points, size):
        b = self._bounding_box(points)
        w, h = b[1] - b[0], b[3] - b[2]
        newPoints = []
        for p in points:
            qx = p[0] * size / w if w > 0 else p[0]
            qy = p[1] * size / h if h > 0 else p[1]
            newPoints.append((qx, qy))
        return newPoints

    def translate_to(self, points, k):
        c = self._centroid(points)
        newPoints = []
        for p in points:
            qx = p[0] + k[0] - c[0]
            qy = p[1] + k[1] - c[1]
            newPoints.append((qx, qy))
        return newPoints

    def distance_at_angle(self, points, template, theta):
        newPoints = self.rotate_by(points, theta)
        return self.path_distance(newPoints, template)

    def distance_at_best_angle(self, points, template, theta_a, theta_b, dtheta):
        x1 = PHI * theta_a + (1 - PHI) * theta_b
        x2 = (1 - PHI) * theta_a + PHI * theta_b
        while abs(theta_b - theta_a) > dtheta:
            f1 = self.distance_at_angle(points, template, x1)
            f2 = self.distance_at_angle(points, template, x2)
            if f1 < f2:
                theta_b = x2
                x2 = x1
                x1 = PHI * theta_a + (1 - PHI) * theta_b
            else:
                theta_a = x1
                x1 = x2
                x2 = (1 - PHI) * theta_a + PHI * theta_b
        return min(self.distance_at_angle(points, template, theta_a), self.distance_at_angle(points, template, theta_b))

    def recognize(self, points):
        points = self.resample(list(points), 64)
        points = self.rotate_by(points, -self.indicative_angle(points))
        points = self.scale_to(points, 250)
        points = self.translate_to(points, (0, 0))

        best_distance = float('inf')
        best = None
        for t in self.templates:
            d = self.distance_at_best_angle(points, t['points'], -math.pi/4, math.pi/4, 0.02)
            if d < best_distance:
                best_distance = d
                best = t

        half_diagonal = 0.5 * math.sqrt(2) * 250
        score = max(0.0, 1.0 - best_distance / half_diagonal)
        return best['name'], score
