class Solution {
    public void merge(int[] nums1, int m, int[] nums2, int n) {
        int i = 0;
        int j = 0;
        int a = 0;
        int[] result = new int[m + n];
        while (i < m && j < n) {
            if (nums1[i] <= nums2[j]) {
                result[a++] = nums1[i++];
            } else {
                result[a++] = nums2[j++];
            }
        }
        while (i < m) {
            result[a++] = nums1[i++];
        }
        while (j < n) {
            result[a++] = nums2[j++];
        }
        for (int s = 0; s < m + n; s++) {
            nums1[s] = result[s];
        }
    }
}