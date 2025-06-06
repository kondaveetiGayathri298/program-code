class Solution {
    public TreeNode invertTree(TreeNode root) {
        if(root==null)
        {
            return null;
        }
        TreeNode temp=root.left; //S
        root.left=root.right;
        root.right=temp;
        invertTree(root.left);   // L
        invertTree(root.right);  // R
        return root;
    }
}