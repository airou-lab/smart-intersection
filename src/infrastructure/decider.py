#!/usr/bin/python3
import rospy
from scripts.square import find_other_corners
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Bool
from scipy.spatial import Delaunay
from ackermann_msgs.msg import AckermannDriveStamped, AckermannDrive

class Decider:
    def __init__(self):
        rospy.init_node('intersection')

        # Intersection box of intersection (x1, y1, x2, y2)
       
        if(rospy.has_param("/smart_infrastructure/static_positions")):
            rospy.loginfo("Static position config found")

        static_positions = rospy.get_param("/smart_infrastructure/static_positions")
        corners = static_positions["intersection_corners"]

        self.intersection_model = Intersection(corners[0], corners[1])

        rospy.loginfo("defined corners: %s", corners)
        rospy.loginfo("inferred corners: %s", find_other_corners((corners[0][0], corners[0][1]), (corners[1][0], corners[1][1])))
        rospy.loginfo("defined velodyne position: %s", static_positions["velodyne"])

        # Subsribers: Car Pose, etc.
        rospy.loginfo("Subscribing...")
        rospy.Subscriber('/car/particle_filter/inferred_pose', PoseStamped, self.car_pose_callback)

        # Publisher for car to read
        self.pub_within = rospy.Publisher('/infrastructure/within_intersection', Bool)
        self.pub_safety = rospy.Publisher('/car/mux/ackermann_cmd_mux/input/safety', AckermannDriveStamped)

    # Execute when new pose is received
    def car_pose_callback(self, msg: PoseStamped):
        # Print pose information
        rospy.loginfo(f"received message {msg}")
        point = (msg.pose.position.x, msg.pose.position.y)
        rospy.loginfo(f"parsed point: {point}")
        
        # Decide if car is contained in intersection
        contains: bool = self.intersection_model.contains(point)
        self.pub_within.publish(Bool(contains))

        # Declare stop command
        if (contains):
            self.stop_car()
    
    def stop_car(self):
        msg = AckermannDriveStamped()
        msg.header.stamp = rospy.Time.now()
        msg.drive.speed = 0.0
        self.pub_safety.publish(msg)
        

# A model of the intersection
class Intersection:
    
    def __init__(self, point1: "tuple[float, float]", point3: "tuple[float, float]"): # Corners of square defining the intersection
        self.points: list[tuple[float, float]]= [point1, point3]
        for p in find_other_corners(point1, point3):
            self.points.append(p)
        self.hull = Delaunay(self.points)


    def contains(self, point: "tuple[float,float]") -> bool:
        # Check containment with simplex
        return (self.hull.find_simplex(point) >= 0)

if __name__ == "__main__":
    try:
        decider = Decider()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass