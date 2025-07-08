from PIL import Image
import os

def resize_images(input_folder, output_folder, image_ids, target_size=(220, 480)):
    """
    批量调整图片尺寸
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    for img_id in image_ids:
        input_path = os.path.join(input_folder, f"{img_id}.jpg")
        output_path = os.path.join(output_folder, f"{img_id}.jpg")
        
        try:
            with Image.open(input_path) as img:
                # 如果图片有透明通道，转换为RGB
                if img.mode in ('LA', 'RGBA', 'P'):
                    img = img.convert('RGB')
                
                resized_img = img.resize(target_size, Image.LANCZOS)
                resized_img.save(output_path)
            print(f"成功处理: {input_path} -> {output_path}")
        except FileNotFoundError:
            print(f"警告: 文件 {input_path} 不存在，跳过处理")
        except Exception as e:
            print(f"处理 {input_path} 时出错: {str(e)}")

if __name__ == "__main__":
    input_folder = r"D:\清华\实践资料\湖南永州\Women_Books-main1\Women_Books-main\图片\女书图片"  # 输入图片所在的文件夹
    output_folder = r"D:\清华\实践资料\湖南永州\Women_Books-main1\Women_Books-main\图片\女书_new"  # 输出图片的文件夹
    image_ids = [34, 73, 98, 126, 135, 189, 191, 195, 197, 203, 217, 232, 239, 240, 241, 266, 278, 304, 320, 327, 332, 338, 341, 344, 
                364, 390, 391, 467, 475, 484, 494, 496, 510, 511, 534, 545, 546, 547, 566, 567, 575, 579, 607, 625, 632, 650, 651, 
                676, 709, 714, 732, 740, 741, 748, 756, 758, 802, 819, 820, 821, 844, 910, 925, 935, 942, 963, 964, 965, 971, 989,
                985, 1025, 1014, 1037, 1133, 1151, 1168, 1198, 1216, 1222, 1279, 1283, 1285, 1330, 1334, 1362, 1365, 1366, 1379,
                1397, 1401, 1402, 1443, 1445, 1453, 1459, 1469, 1471, 1512, 1529, 1535, 1537, 1548, 1553, 1558, 1576, 1578, 1579,
                1599, 1607, 1658, 1671, 1688]  # 需要处理的图片ID列表
    
    resize_images(input_folder, output_folder, image_ids)