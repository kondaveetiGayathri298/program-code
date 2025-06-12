class Solution {
    public boolean isValidSudoku(char[][] b) {
        for (int i = 0; i < 9; i++) {
            for (int j = 0; j < 9; j++) {
                if (b[i][j] != '.') {
                    for (int k = i + 1; k < 9; k++) 
                        if (b[k][j] == b[i][j]) return false;

                    for (int k = j + 1; k < 9; k++) 
                        if (b[i][k] == b[i][j]) return false;

                    for (int k = j - 1; k >= 0; k--) 
                        if (b[i][k] == b[i][j]) return false;

                    int r = (i / 3) * 3, c = (j / 3) * 3;
                    for (int x = r; x < r + 3; x++) {
                        for (int y = c; y < c + 3; y++) {
                            if ((x != i || y != j) && b[x][y] == b[i][j]) 
                                return false;
                        }
                    }
                }
            }
        }
        return true;
    }
}
